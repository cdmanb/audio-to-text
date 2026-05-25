"""语音识别引擎 —— 通过 oMLX 调用 Qwen3-ASR，长音频自动分段"""

import io
import os
import time
import tempfile
import wave
from abc import ABC, abstractmethod
from pathlib import Path

import soundfile as sf
from openai import APIConnectionError

MAX_RETRIES = 3
RETRY_DELAY = 5
CHUNK_SECONDS = 600  # 每段 10 分钟


class BaseASR(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str | Path) -> str:
        ...


class OMLXASR(BaseASR):
    def __init__(self, api_key: str = "omlx", base_url: str = "http://localhost:8000/v1",
                 model: str = "Qwen3-ASR-1.7B-8bit"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = None
        self._aborted = False

    def _get_client(self):
        if self._aborted:
            raise RuntimeError("已中止")
        if self._client is None:
            from openai import OpenAI
            import httpx
            self._client = OpenAI(
                api_key=self.api_key, base_url=self.base_url, max_retries=0,
                timeout=httpx.Timeout(600.0, connect=10.0),
            )
        return self._client

    def abort(self):
        self._aborted = True
        if self._client:
            try: self._client.close()
            except Exception: pass
            self._client = None

    def transcribe(self, audio_path: str | Path, progress_callback=None) -> str:
        audio_path = str(audio_path)
        info = sf.info(audio_path)
        sr = info.samplerate
        duration = info.duration

        if duration <= CHUNK_SECONDS + 30:
            if progress_callback:
                progress_callback("transcribing", f"ASR 转写中...")
            return self._transcribe_file(audio_path)

        total_chunks = max(int(duration / CHUNK_SECONDS) + 1, 1)
        results = []
        pos = 0.0
        idx = 0
        while pos < duration - 5:
            if self._aborted:
                break
            idx += 1
            end = min(pos + CHUNK_SECONDS + 3, duration)
            if progress_callback:
                progress_callback("transcribing", f"ASR 转写 ({idx}/{total_chunks})")
            chunk_path = self._write_chunk(audio_path, pos, end, sr)
            try:
                text = self._transcribe_file(chunk_path)
                if text:
                    results.append(text)
            finally:
                try: os.unlink(chunk_path)
                except Exception: pass
            if self._aborted:
                break
            pos = end - 3

        return "\n\n".join(results)

    def _write_chunk(self, audio_path: str, start: float, end: float, sr: int) -> str:
        data, _ = sf.read(audio_path, start=int(start*sr), stop=int(end*sr), dtype="int16")
        if data.ndim > 1:
            data = data.mean(axis=1).astype("int16")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(data.tobytes())
        return tmp.name

    def _transcribe_file(self, path: str) -> str:
        client = self._get_client()
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                with open(path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model=self.model,
                        file=(os.path.basename(path), f, "audio/wav"),
                        language="zh",
                        response_format="text",
                    )
                return result.strip()
            except APIConnectionError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        raise last_error
