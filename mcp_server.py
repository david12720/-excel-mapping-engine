import sys
from pathlib import Path

# Make engine importable when run directly
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from mcp.server.fastmcp import FastMCP

from engine import source_reader
from engine.orchestrator import RunConfig, run
from engine.strategies import DefaultFirstMatchStrategy, MirrorStrategy

mcp = FastMCP("Excel Mapping Engine")


@mcp.tool()
def list_files(source_root: str) -> list[str]:
    """List all Excel files found recursively under source_root."""
    root = Path(source_root)
    if not root.exists():
        return [f"Error: '{source_root}' does not exist"]
    return sorted(str(p.relative_to(root)) for p in root.rglob("*.xlsx"))


@mcp.tool()
def list_keys(file_path: str, sheet_name: str, key_column: str, header_row: int) -> list[str]:
    """Return all non-null values from key_column in the given sheet.
    Use this to discover available keys before running mirror or search mode."""
    df = source_reader.load_sheet(Path(file_path), sheet_name, header_row)
    if df is None:
        return [f"Error: sheet '{sheet_name}' not found in '{file_path}'"]
    if key_column not in df.columns:
        return [f"Error: column '{key_column}' not found. Available columns: {list(df.columns)}"]
    return [str(k) for k in df[key_column].dropna().tolist()]


@mcp.tool()
def run_mirror(
    source_root: str,
    target_filenames: list[str],
    source_sheet_name: str,
    key_column: str,
    value_column: str,
    master_id_column: str,
    header_row: int,
    skip_keys: list[str] = [],
    master_file_path: str = "",
) -> dict:
    """Run mirror mode: map every row of the source sheet into the master file.
    key_column values become master column names; value_column values become the data.
    Optionally provide skip_keys to exclude specific rows.
    master_file_path is auto-generated as master_mirror.xlsx in source_root if not supplied."""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_mirror.xlsx")

    config = RunConfig(
        source_root=source_root,
        target_filenames=target_filenames,
        source_sheet_name=source_sheet_name,
        mode="mirror",
        key_column=key_column,
        value_column=value_column,
        master_id_column=master_id_column,
        header_row=header_row,
        skip_keys=skip_keys,
        master_file_path=master_file_path,
        strategy=MirrorStrategy(),
    )

    run(config)

    df = pd.read_excel(master_file_path)
    return {
        "master_file": master_file_path,
        "rows": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }


@mcp.tool()
def run_search(
    source_root: str,
    target_filenames: list[str],
    source_sheet_name: str,
    filter_column_label: str,
    search_term: str,
    data_source_column: str,
    master_target_column: str,
    master_id_column: str,
    header_row: int,
    master_file_path: str = "",
) -> dict:
    """Run search mode: find the first row matching search_term in filter_column_label
    and extract the value from data_source_column for each target file.
    master_file_path is auto-generated as master_search.xlsx in source_root if not supplied."""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_search.xlsx")

    config = RunConfig(
        source_root=source_root,
        target_filenames=target_filenames,
        source_sheet_name=source_sheet_name,
        mode="search",
        filter_column_label=filter_column_label,
        search_term=search_term,
        data_source_column=data_source_column,
        master_target_column=master_target_column,
        master_id_column=master_id_column,
        header_row=header_row,
        master_file_path=master_file_path,
        strategy=DefaultFirstMatchStrategy(),
    )

    run(config)

    df = pd.read_excel(master_file_path)
    return {
        "master_file": master_file_path,
        "rows": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }


if __name__ == "__main__":
    mcp.run()
