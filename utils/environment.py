"""Load the single supported local secret without overriding shell settings."""
import os
from pathlib import Path


def load_environment():
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key.strip() == "DASHSCOPE_API_KEY":
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not key or key == "replace-with-your-own-key":
        raise RuntimeError("请复制 .env.example 为 .env，填写 DASHSCOPE_API_KEY，或设置同名环境变量。")
