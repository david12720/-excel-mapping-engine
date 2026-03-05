import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def find_files(source_root: str, target_filenames: list[str]) -> dict[str, Path]:
    root = Path(source_root)
    found: dict[str, Path] = {}

    for path in root.rglob("*.xlsx"):
        if path.stem in target_filenames:
            found[path.stem] = path

    for name in target_filenames:
        if name not in found:
            logger.warning("Target file not found: '%s' under '%s'", name, source_root)

    return found


def load_sheet(file_path: Path, sheet_name: str, header_row: int = 0) -> pd.DataFrame | None:
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, header=header_row, engine="openpyxl")
    except Exception as e:
        logger.warning("Sheet '%s' not found in '%s': %s", sheet_name, file_path, e)
        return None
