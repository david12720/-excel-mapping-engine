from pathlib import Path
from typing import Any

import pandas as pd


def upsert(
    master_df: pd.DataFrame,
    key: str,
    master_target_column: str,
    value: Any,
) -> pd.DataFrame:
    """Pure function — no file I/O. Returns a new DataFrame with the upserted value."""
    df = master_df.copy()
    id_col = df.columns[0]

    # Compare as strings to avoid int/str mismatches when pandas reads the file back
    row_mask = df[id_col].astype(str) == str(key)
    if not row_mask.any():
        new_row = {col: None for col in df.columns}
        new_row[id_col] = key
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        row_mask = df[id_col] == key

    if master_target_column not in df.columns:
        df[master_target_column] = None

    row_idx = df.index[row_mask][0]
    df.at[row_idx, master_target_column] = value
    return df


def load_master(master_file_path: str, id_column: str = "id") -> pd.DataFrame:
    path = Path(master_file_path)
    if not path.exists():
        return pd.DataFrame(columns=[id_column])
    return pd.read_excel(master_file_path, engine="openpyxl")


def save_master(master_df: pd.DataFrame, master_file_path: str) -> None:
    Path(master_file_path).parent.mkdir(parents=True, exist_ok=True)
    master_df.to_excel(master_file_path, index=False, engine="openpyxl")
