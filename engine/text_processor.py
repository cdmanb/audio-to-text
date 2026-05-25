"""文本处理管线 —— Cleaner → LLM → Output（无需 ASR）"""

import traceback
import os

from cleaner.text_cleaner import clean_text
from engine.llm import OpenAICompatibleLLM
from output.writer import write_transcript, write_summary


class TextResult:
    def __init__(self, file_path: str, output_paths: list[str] | None = None, error: str = ""):
        self.file_path = file_path
        self.output_paths = output_paths or []
        self.error = error
        self.success = not bool(error)

    @property
    def output_path(self) -> str:
        return "\n".join(self.output_paths) if self.output_paths else ""


class TextProcessor:
    def __init__(self, llm: OpenAICompatibleLLM, output_dir: str,
                 remove_fillers: bool = True, remove_repetitions: bool = True,
                 generate_summary: bool = True, summary_dir: str = ""):
        self.llm = llm
        self.output_dir = output_dir
        self.summary_dir = summary_dir or output_dir
        self.remove_fillers = remove_fillers
        self.remove_repetitions = remove_repetitions
        self.generate_summary = generate_summary
        self._stopped = False

    def stop(self):
        self._stopped = True
        self.llm.abort()

    def process(self, file_path: str, progress_callback=None) -> TextResult:
        self._stopped = False
        try:
            base = os.path.basename(file_path)

            if progress_callback:
                progress_callback("reading", f"读取: {base}")

            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            if not raw_text.strip():
                return TextResult(file_path, error="文件内容为空")

            if self._stopped:
                return TextResult(file_path, error="已停止")

            if progress_callback:
                progress_callback("cleaning", "清洗文本...")

            cleaned = clean_text(raw_text, self.remove_fillers, self.remove_repetitions)
            if self._stopped:
                return TextResult(file_path, error="已停止")

            if progress_callback:
                progress_callback("proofreading", f"校对 [{self.llm.model}]...")

            proofread = self.llm.proofread(cleaned)
            if self._stopped:
                return TextResult(file_path, error="已停止")

            is_local = "localhost" in self.llm.base_url or "127.0.0.1" in self.llm.base_url
            llm_label = f"oMLX ({self.llm.model})" if is_local else self.llm.model

            if progress_callback:
                progress_callback("writing", "写入校对稿...")

            output_paths = []
            output_paths.append(write_transcript(
                audio_name=file_path, proofread_text=proofread,
                output_dir=self.output_dir, asr_model="文本输入（无ASR）", llm_backend=llm_label,
            ))

            if self.generate_summary:
                if progress_callback:
                    progress_callback("summarizing", f"摘要 [{self.llm.model}]...")
                summary = self.llm.summarize(proofread)
                if self._stopped:
                    return TextResult(file_path, error="已停止")
                if progress_callback:
                    progress_callback("writing", "写入摘要...")
                output_paths.append(write_summary(
                    audio_name=file_path, summary=summary,
                    output_dir=self.summary_dir, llm_backend=llm_label,
                ))

            return TextResult(file_path, output_paths)

        except Exception as e:
            return TextResult(file_path, error=f"{e}\n{traceback.format_exc()}")
