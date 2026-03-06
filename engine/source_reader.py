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


def load_target_list(
    file_path: str,
    sheet_name: str,
    column_name: str,
    header_row: int,
) -> list[str] | None:
    """Load filename stems from a column in an Excel file.
    Returns a list of stems, or None if the sheet/column is not found."""
    df = load_sheet(Path(file_path), sheet_name, header_row)
    if df is None:
        return None
    if column_name not in df.columns:
        logger.warning("Column '%s' not found in '%s'. Available: %s", column_name, file_path, list(df.columns))
        return None
    def _to_stem(v) -> str:
        # pandas reads numeric stems as float when nulls exist (e.g. 123 → 123.0)
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)

    return [_to_stem(v) for v in df[column_name].dropna().tolist()]


def load_sheet(file_path: Path, sheet_name: str, header_row: int = 0) -> pd.DataFrame | None:
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, header=header_row, engine="openpyxl")
    except Exception as e:
        logger.warning("Sheet '%s' not found in '%s': %s", sheet_name, file_path, e)
        return None
