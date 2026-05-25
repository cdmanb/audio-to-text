""".md 转写文档输出"""

from datetime import datetime
from pathlib import Path


def write_transcript(
    audio_name: str,
    proofread_text: str,
    output_dir: str | Path,
    asr_model: str = "",
    llm_backend: str = "",
) -> str:
    """生成校对后的转写 .md 文档"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = Path(audio_name).stem
    base = base.replace("NebulaRec-", "")
    output_path = output_dir / f"{base}_校对稿.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""# {base} —— 校对稿

> **生成时间**: {timestamp}
> **音频文件**: {audio_name}
> **ASR 模型**: {asr_model}
> **校对模型**: {llm_backend}

---

{proofread_text}
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return str(output_path)


def write_summary(
    audio_name: str,
    summary: str,
    output_dir: str | Path,
    llm_backend: str = "",
) -> str:
    """生成重点摘要 .md 文档"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = Path(audio_name).stem
    base = base.replace("NebulaRec-", "")
    output_path = output_dir / f"{base}_重点摘要.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""# {base} —— 重点摘要

> **生成时间**: {timestamp}
> **音频文件**: {audio_name}
> **生成模型**: {llm_backend}

---

{summary}
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return str(output_path)
