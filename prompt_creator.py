"""Template loading for prompts."""

from pathlib import Path

_BASE = Path(__file__).parent
_TPL = _BASE / "templates"


def _read(path):
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def get_main_prompt():
    return _read(_TPL / "prompt-template.txt")


def get_cover_prompt():
    return _read(_TPL / "cover-letter-template.txt")
