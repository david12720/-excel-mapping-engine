import sys
from pathlib import Path

# Make engine importable when run directly
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from mcp.server.fastmcp import FastMCP

from engine import source_reader
from engine.orchestrator import RunConfig, run
from engine.strategies import DefaultFirstMatchStrategy, MirrorStrategy

mcp = FastMCP(
    "Excel Mapping Engine",
    instructions="""You are working with an Excel mapping engine.

IMPORTANT RULES:
- ALWAYS use the excel-engine tools for any operation involving Excel files, directories, or paths.
- NEVER use your own file system tools or code execution to read, list, or process Excel files.
- NEVER ask the user to upload files. The files already exist on disk. Ask for the folder path instead.
- When starting a session, ask the user: "What is the root folder path where your Excel files are located?" then call list_files(source_root=<path>).
- When the user asks about available fields or columns, use list_keys() — do not try to read the file yourself.
- When the user wants to extract or mirror data, use run_mirror() or run_search() — do not write code to do it.

WORKFLOW:
1. list_files → discover available file stems
2. list_keys → discover available columns and keys in a sheet
3. BEFORE calling run_mirror or run_search: ask the user about every optional parameter explicitly:
   - For run_mirror: ask "Which keys would you like to skip? (or none)" and "Where should the master file be saved? (or leave blank for auto)"
   - For run_search: ask "Where should the master file be saved? (or leave blank for auto)"
4. Only call run_mirror or run_search after the user has answered all optional parameter questions.

NEVER skip asking about optional parameters. NEVER assume default values silently.
""",
)


def _stems(filenames: list[str]) -> list[str]:
    """Strip extensions from filenames so target_filenames always contains stems.
    Handles both '123' and '123.xlsx' gracefully."""
    return [Path(f).stem for f in filenames]


@mcp.tool()
def list_files(source_root: str) -> dict:
    """List all Excel files found recursively under source_root.
    Returns stems (pass these directly as target_filenames) and full relative paths."""
    root = Path(source_root)
    if not root.exists():
        return {"error": f"'{source_root}' does not exist"}
    files = sorted(root.rglob("*.xlsx"))
    return {
        "stems": [p.stem for p in files],
        "paths": [str(p.relative_to(root)) for p in files],
    }


@mcp.tool()
def list_keys(file_path: str, sheet_name: str, key_column: str, header_row: int) -> dict:
    """Return all non-null values from key_column in the given sheet.
    Also returns all available column names so you can verify key_column and value_column.
    Use this before running mirror or search mode."""
    df = source_reader.load_sheet(Path(file_path), sheet_name, header_row)
    if df is None:
        return {"error": f"Sheet '{sheet_name}' not found in '{file_path}'"}
    if key_column not in df.columns:
        return {
            "error": f"Column '{key_column}' not found",
            "available_columns": list(df.columns),
        }
    return {
        "available_columns": list(df.columns),
        "keys": [str(k) for k in df[key_column].dropna().tolist()],
    }


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
    target_filenames: pass stems only e.g. ['123', '999'] — use list_files to discover them.
    skip_keys: optional list of key values to exclude.
    master_file_path: auto-generated as master_mirror.xlsx in source_root if not supplied."""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_mirror.xlsx")

    # Strip extensions defensively in case LLM passes '123.xlsx'
    stems = _stems(target_filenames)

    # Validate files exist before running
    files_found = source_reader.find_files(source_root, stems)
    if not files_found:
        return {
            "error": "No matching files found.",
            "source_root": source_root,
            "target_filenames_received": target_filenames,
            "stems_searched": stems,
            "hint": "Use list_files(source_root) to see available stems.",
        }

    config = RunConfig(
        source_root=source_root,
        target_filenames=stems,
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
        "files_processed": list(files_found.keys()),
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
    """Run search mode: opens each target file, finds the first row where filter_column_label
    contains search_term, and extracts the value from data_source_column.
    One value per file is written into a single master column (master_target_column).
    This is NOT for searching across files — use list_files for that.
    target_filenames: pass stems only e.g. ['123', '999'] — use list_files to discover them.
    master_file_path: auto-generated as master_search.xlsx in source_root if not supplied."""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_search.xlsx")

    # Strip extensions defensively in case LLM passes '123.xlsx'
    stems = _stems(target_filenames)

    # Validate files exist before running
    files_found = source_reader.find_files(source_root, stems)
    if not files_found:
        return {
            "error": "No matching files found.",
            "source_root": source_root,
            "target_filenames_received": target_filenames,
            "stems_searched": stems,
            "hint": "Use list_files(source_root) to see available stems.",
        }

    config = RunConfig(
        source_root=source_root,
        target_filenames=stems,
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
        "files_processed": list(files_found.keys()),
        "rows": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }


if __name__ == "__main__":
    mcp.run()
