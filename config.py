"""应用配置管理"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".audio-to-text"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "asr": {
        "base_url": "http://localhost:8000/v1",
        "api_key": "omlx",
        "model": "Qwen3-ASR-1.7B-8bit",
    },
    "llm": {
        "backend": "omlx",
        "omlx": {
            "base_url": "http://localhost:8000/v1",
            "api_key": "omlx",
            "model": "Qwen3.6-35B-A3B-8bit",
        },
        "openai": {
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o",
        },
    },
    "output_dir": str(Path.home() / "AudioTranscriptions"),
    "summary_dir": "",
    "cleaner": {
        "remove_fillers": True,
        "remove_repetitions": True,
    },
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return _deep_merge(DEFAULT_CONFIG.copy(), saved)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
