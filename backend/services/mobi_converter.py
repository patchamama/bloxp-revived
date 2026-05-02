import subprocess
from pathlib import Path
from typing import Optional

from config import settings


def convert_epub_to_mobi(epub_path: Path, mobi_path: Path) -> Optional[str]:
    """Returns error string if conversion fails, None on success."""
    try:
        cmd = settings.calibre_ebook_convert_path or "ebook-convert"
        result = subprocess.run(
            [cmd, str(epub_path), str(mobi_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return result.stderr or "ebook-convert failed"
        return None
    except (FileNotFoundError, PermissionError, OSError):
        return f"Calibre not installed or not executable at '{settings.calibre_ebook_convert_path}' — Mobi conversion unavailable"
    except subprocess.TimeoutExpired:
        return "Mobi conversion timed out"
