"""Template loading for prompts."""

from pathlib import Path

from exceptions import TemplateNotFoundError

_BASE = Path(__file__).parent
_TPL = _BASE / "templates"


def _read(path: Path) -> str:
    """Read template file.

    Args:
        path: Path to template file

    Returns:
        Template content

    Raises:
        TemplateNotFoundError: If template file doesn't exist
    """
    if not path.exists():
        raise TemplateNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def get_main_prompt() -> str:
    """Get the main resume prompt template.

    Returns:
        Prompt template content
    """
    return _read(_TPL / "prompt-template.txt")


def get_cover_prompt() -> str:
    """Get the cover letter prompt template.

    Returns:
        Cover letter prompt template content
    """
    return _read(_TPL / "cover-letter-template.txt")
