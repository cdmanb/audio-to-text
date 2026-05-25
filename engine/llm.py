"""LLM 引擎 —— OpenAI 兼容 API"""

import time
import re
from abc import ABC, abstractmethod

from openai import APIConnectionError

PROOFREAD_SYSTEM = "你是专业的中文讲话稿整理助手。请将以下语音转写文本整理为一份完整规范的中文讲话稿：1.修正同音错别字和语法错误；2.将碎片化口语整合为通顺书面语句；3.按逻辑合理分段；4.保留全部原意和细节，不删减内容。直接输出讲话稿正文，禁止思考或分析。"

SUMMARIZE_PROMPT = """请对以下文档提取重点内容，要求：

1. 按原文的段落和逻辑结构，分层列出每个部分的核心内容
2. 使用 markdown 层级标题和列表，层次分明
3. 保留原文的关键细节、数据、观点和论据，不要过度精简
4. 每个要点应该是一句完整的话，能独立理解

输出格式：

# 文档标题（根据内容概括）

## 一、[第一部分的主题]
- 要点1：完整描述
- 要点2：完整描述

## 二、[第二部分的主题]
- ...

原文："""

MAX_RETRIES = 3
RETRY_DELAY = 5


class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> str:
        ...

    def proofread(self, text: str) -> str:
        max_tok = 131072
        return self.generate(text, PROOFREAD_SYSTEM, max_tokens=max_tok)

    def summarize(self, text: str) -> str:
        max_tok = 32768
        return self.generate(SUMMARIZE_PROMPT + "\n\n" + text, "", max_tokens=max_tok)


class OpenAICompatibleLLM(BaseLLM):

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o"):
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
                timeout=httpx.Timeout(1800.0, connect=10.0),
            )
        return self._client

    def abort(self):
        self._aborted = True
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    @staticmethod
    def _strip_thinking(text: str) -> str:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        lines = text.split("\n")
        start = 0
        for i, line in enumerate(lines):
            s = line.strip()
            if not s:
                continue
            cn = sum(1 for c in s if "一" <= c <= "鿿")
            ratio = cn / len(s) if len(s) > 0 else 0
            if ratio > 0.5 and not re.match(r"^[\d\-\*]+[\.\)]\s*\*", s) and "**" not in s[:5]:
                for j in range(i - 1, max(i - 3, 0), -1):
                    if not lines[j].strip():
                        start = j + 1
                        break
                else:
                    start = i
                break
        text = "\n".join(lines[start:]).strip()
        text = re.sub(r"\*Segment \d+\*:.*?\n", "", text)
        text = re.sub(r"\*\*\(.*?\)\*\*", "", text)
        return text.strip()

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        client = self._get_client()
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=max_tokens,
                )
                return self._strip_thinking(response.choices[0].message.content)
            except APIConnectionError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        raise RuntimeError("oMLX 连接失败（可能内存不足崩溃），请检查 oMLX 是否在运行。") from last_error
