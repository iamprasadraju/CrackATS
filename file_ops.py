"""File operations for job folder creation."""

import logging
import shutil
import textwrap
from pathlib import Path

from exceptions import FileOperationError, TemplateNotFoundError

logger = logging.getLogger(__name__)


def ensure_job_folder(base_dir: str | Path, folder_name: str) -> Path:
    """Ensure job folder exists, creating it if necessary.

    Args:
        base_dir: Base directory path
        folder_name: Name of the folder to create

    Returns:
        Path object for the created folder
    """
    path = Path(base_dir) / folder_name
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured job folder exists: {path}")
    return path


def _wrap(text: str | None, width: int = 80) -> str:
    """Wrap text to specified width.

    Args:
        text: Text to wrap
        width: Maximum line width

    Returns:
        Wrapped text
    """
    lines: list[str] = []
    for raw in (text or "").splitlines():
        ln = raw.strip()
        if not ln:
            lines.append("")
        else:
            lines.extend(textwrap.fill(ln, width, break_long_words=False, break_on_hyphens=False).splitlines())
    return "\n".join(lines)


def write_description(
    folder: Path,
    filename: str,
    description: str,
    width: int = 80,
    source_url: str | None = None,
) -> Path:
    """Write job description to file.

    Args:
        folder: Target folder path
        filename: Name of the file to create
        description: Job description text
        width: Text wrap width
        source_url: Optional source URL to include

    Returns:
        Path object for the created file
    """
    path = folder / filename
    parts: list[str] = []
    if source_url:
        parts.extend([f"Source: {source_url.strip()}", ""])
    if text := _wrap(description, width).rstrip():
        parts.append(text)
    path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    logger.debug(f"Wrote description to: {path}")
    return path


def write_prompt_file(
    folder: Path,
    filename: str,
    prompt: str,
    description: str,
    width: int = 80,
) -> Path:
    """Write prompt file with description.

    Args:
        folder: Target folder path
        filename: Name of the file to create
        prompt: Prompt text
        description: Job description text
        width: Text wrap width

    Returns:
        Path object for the created file
    """
    path = folder / filename
    parts = [p for p in [_wrap(prompt, width).rstrip(), _wrap(description, width).rstrip()] if p]
    path.write_text("\n\n".join(parts).rstrip() + "\n", encoding="utf-8")
    logger.debug(f"Wrote prompt file to: {path}")
    return path


def copy_template(
    template_path: Path,
    target_dir: Path,
    target_name: str | None = None,
) -> Path | None:
    """Copy template file to target directory.

    Args:
        template_path: Path to the template file
        target_dir: Target directory
        target_name: Optional new name for the file

    Returns:
        Path to the copied file, or None if template doesn't exist

    Raises:
        TemplateNotFoundError: If template file doesn't exist
    """
    if not template_path.exists():
        raise TemplateNotFoundError(f"Template not found: {template_path}")

    target = target_dir / (target_name or template_path.name)
    if not target.exists():
        shutil.copyfile(template_path, target)
        logger.debug(f"Copied template from {template_path} to {target}")
    return target


def safe_write_text(filepath: Path, content: str) -> None:
    """Safely write text to file with validation.

    Args:
        filepath: Path to write to
        content: Content to write

    Raises:
        FileOperationError: If write fails
    """
    try:
        filepath.write_text(content, encoding="utf-8")
        logger.debug(f"Wrote file: {filepath}")
    except Exception as e:
        raise FileOperationError(f"Failed to write file: {filepath}", details=str(e)) from e


def safe_read_text(filepath: Path) -> str:
    """Safely read text from file.

    Args:
        filepath: Path to read from

    Returns:
        File contents

    Raises:
        FileOperationError: If read fails
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        logger.debug(f"Read file: {filepath}")
        return content
    except Exception as e:
        raise FileOperationError(f"Failed to read file: {filepath}", details=str(e)) from e
