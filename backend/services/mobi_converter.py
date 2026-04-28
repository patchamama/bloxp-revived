import subprocess
from pathlib import Path
from typing import Optional


def convert_epub_to_mobi(epub_path: Path, mobi_path: Path) -> Optional[str]:
    """Returns error string if conversion fails, None on success."""
    try:
        result = subprocess.run(
            ["ebook-convert", str(epub_path), str(mobi_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return result.stderr or "ebook-convert failed"
        return None
    except FileNotFoundError:
        return "Calibre not installed — Mobi conversion unavailable"
    except subprocess.TimeoutExpired:
        return "Mobi conversion timed out"
