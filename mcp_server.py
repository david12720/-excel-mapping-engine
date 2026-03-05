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
    instructions="""You are operating an Excel mapping engine. All Excel files live on the user's local disk.

STRICT RULES — follow in every session:
1. NEVER ask the user to upload files. Files are on disk. Always work with paths.
2. NEVER use your own file/code tools. Only use the excel-engine tools provided.
3. ALWAYS start by calling begin() — this is the entry point for every session.
4. NEVER call run_mirror or run_search without first completing the begin() conversation flow.
5. If a tool returns "master_file_conflict", ask the user for a new filename before retrying.
""",
)


def _stems(filenames: list[str]) -> list[str]:
    """Strip extensions so target_filenames always contains stems."""
    return [Path(f).stem for f in filenames]


def _suggest_name(path: Path) -> str:
    """Suggest an alternative filename by appending _1, _2, etc."""
    i = 1
    while True:
        candidate = path.parent / f"{path.stem}_{i}{path.suffix}"
        if not candidate.exists():
            return str(candidate)
        i += 1


@mcp.tool()
def begin(root_path: str) -> dict:
    """ALWAYS call this first. Entry point for every session.
    Ask the user: 'What is the root folder path where your Excel files are located?'
    then call begin(root_path=<their answer>).
    Returns file count and asks the user if they want to list the files."""
    root = Path(root_path)
    if not root.exists():
        return {"error": f"'{root_path}' does not exist. Please check the path and try again."}

    files = sorted(root.rglob("*.xlsx"))

    return {
        "root_path": root_path,
        "total_files": len(files),
        "next_steps": (
            "Tell the user how many Excel files were found, then ask: "
            "'Would you like to see the list of available files?' "
            "If yes: call list_files(root_path). If no: ask the user to type the filenames they want to process. "
            "Then ask: "
            "1. Which mode: mirror or search? "
            "2. What is the sheet name? "
            "3. What is the header row index (0 = first row)? "
            "4. What is the key column name (mirror) or filter column name (search)? "
            "5. What is the value column name (mirror) or search term + data column (search)? "
            "6. What is the master ID column name? "
            "Then ask: 'Would you like to see the available keys in the sheet before running?' "
            "If yes: call list_keys. If no: skip. "
            "Then ask: 'Are there any keys to skip? (mirror only — type them or leave blank for none)' "
            "Then ask: 'Where to save the master file? (leave blank for auto)'"
        ),
    }


@mcp.tool()
def list_files(root_path: str) -> dict:
    """List all Excel file stems and absolute paths under root_path.
    Call this only if the user asks to see the available files.
    Pass stems (not paths) to target_filenames in run_mirror or run_search."""
    root = Path(root_path)
    if not root.exists():
        return {"error": f"'{root_path}' does not exist"}
    files = sorted(root.rglob("*.xlsx"))
    return {
        "stems": [p.stem for p in files],
        "absolute_paths": [str(p.resolve()) for p in files],
    }


@mcp.tool()
def list_keys(file_path: str, sheet_name: str, key_column: str, header_row: int) -> dict:
    """Show all available keys from key_column in the given sheet.
    Call this only if the user asks to see available keys before running.
    Also returns available column names to help verify column name inputs.
    Use absolute paths from begin() or list_files() for file_path."""
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
    target_filenames: stems only e.g. ['123', '999'] — from list_files() results.
    skip_keys: keys to exclude (ask the user before calling).
    master_file_path: auto-generated as master_mirror.xlsx in source_root if blank.
    If master file already exists, returns master_file_conflict — ask user for a new name."""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_mirror.xlsx")

    if Path(master_file_path).exists():
        return {
            "master_file_conflict": True,
            "existing_file": master_file_path,
            "suggested_name": _suggest_name(Path(master_file_path)),
            "action": "Ask the user: 'The file already exists. Provide a new name or use the suggested one.'",
        }

    stems = _stems(target_filenames)
    files_found = source_reader.find_files(source_root, stems)
    if not files_found:
        return {
            "error": "No matching files found.",
            "stems_searched": stems,
            "hint": "Call list_files(root_path) to see available stems.",
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
    """Run search mode: opens each target file, finds the first row where
    filter_column_label contains search_term, extracts the value from data_source_column.
    One value per file is written into master_target_column in the master file.
    This is NOT for searching across files — begin() handles file discovery.
    target_filenames: stems only e.g. ['123', '999'] — from list_files() results.
    master_file_path: auto-generated as master_search.xlsx in source_root if blank.
    If master file already exists, returns master_file_conflict — ask user for a new name."""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_search.xlsx")

    if Path(master_file_path).exists():
        return {
            "master_file_conflict": True,
            "existing_file": master_file_path,
            "suggested_name": _suggest_name(Path(master_file_path)),
            "action": "Ask the user: 'The file already exists. Provide a new name or use the suggested one.'",
        }

    stems = _stems(target_filenames)
    files_found = source_reader.find_files(source_root, stems)
    if not files_found:
        return {
            "error": "No matching files found.",
            "stems_searched": stems,
            "hint": "Call list_files(root_path) to see available stems.",
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
