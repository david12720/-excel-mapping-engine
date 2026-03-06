import json
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
3. ALWAYS start by calling begin() — no parameters needed. It is the entry point for every session.
4. NEVER call run_mirror or run_search without completing the full conversation flow first.
5. If a tool returns "master_file_conflict", ask the user to choose override/merge/rename before retrying.
6. NEVER ask more than one question at a time. Ask one question, wait for the answer, then ask the next.
7. After a successful run, always ask: "Would you like to save these settings for future sessions?"
   If yes: call save_session() with a name provided by the user.
""",
)

SESSIONS_FILE = Path(__file__).parent / "config" / "sessions.json"


def _load_sessions() -> dict:
    if not SESSIONS_FILE.exists():
        return {}
    with open(SESSIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_sessions(sessions: dict) -> None:
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def _stems(filenames: list[str]) -> list[str]:
    return [Path(f).stem for f in filenames]


def _suggest_name(path: Path) -> str:
    i = 1
    while True:
        candidate = path.parent / f"{path.stem}_{i}{path.suffix}"
        if not candidate.exists():
            return str(candidate)
        i += 1


@mcp.tool()
def begin() -> dict:
    """ALWAYS call this first. No parameters needed.
    Loads saved sessions and returns them so the user can choose to reuse one or start fresh."""
    sessions = _load_sessions()

    if sessions:
        return {
            "saved_sessions": sessions,
            "next_steps": (
                "Show the user their saved sessions clearly (name + key settings). "
                "Ask: 'Would you like to use a saved session or start fresh?' "
                "If saved session chosen: if the session has target_list_file set, call load_target_list() "
                "to reload the stems fresh from that file (the list may have changed). "
                "Then confirm each setting with the user ONE AT A TIME before running — "
                "they may want to change some values. "
                "If fresh start: ask for the root folder path, then call start_session(root_path)."
            ),
        }

    return {
        "saved_sessions": {},
        "next_steps": "No saved sessions found. Ask the user for their root folder path, then call start_session(root_path).",
    }


@mcp.tool()
def start_session(root_path: str) -> dict:
    """Call after begin() when starting fresh (no saved session selected).
    Validates the root path and returns file count.
    Then follow the Q1-Q9 conversation flow."""
    root = Path(root_path)
    if not root.exists():
        return {"error": f"'{root_path}' does not exist. Please check the path and try again."}

    files = sorted(root.rglob("*.xlsx"))

    return {
        "root_path": root_path,
        "total_files": len(files),
        "next_steps": (
            "Ask questions ONE AT A TIME — wait for the answer before asking the next. "
            "Q1: 'How would you like to specify the files to process? "
            "(a) From an Excel list file — ask for its path, sheet, column name and header row, then call load_target_list(); "
            "(b) Browse available files — call list_files(root_path); "
            "(c) Type filenames manually.' "
            "Show the loaded/typed stems to the user and confirm before continuing. "
            "Q2: 'Which mode: mirror or search?' "
            "Q3: 'What is the sheet name?' "
            "Q4: 'What is the header row index? (0 = first row)' "
            "Q5 (mirror): 'What is the key column name?' / (search): 'What is the filter column name?' "
            "Q6 (mirror): 'What is the value column name?' / (search): 'What is the search term?' "
            "Q6b (search only): 'What is the data source column name?' "
            "Q6c (search only): 'What should the master target column be called?' "
            "Q7: 'Would you like to see the available keys in the sheet first?' — if yes call list_keys, if no continue. "
            "Q8 (mirror only): 'Are there any keys you want to skip? Type them or press Enter for none.' "
            "Q9: 'Where should the master file be saved? Leave blank for auto.'"
        ),
    }


@mcp.tool()
def save_session(
    session_name: str,
    source_root: str,
    source_sheet_name: str,
    header_row: int,
    mode: str,
    target_filenames: list[str] = [],
    target_list_file: str = "",
    target_list_sheet: str = "",
    target_list_column: str = "",
    target_list_header_row: int = 0,
    key_column: str = "",
    value_column: str = "",
    filter_column_label: str = "",
    search_term: str = "",
    data_source_column: str = "",
    master_target_column: str = "",
    skip_keys: list[str] = [],
    master_id_column: str = "מספר בקשה",
) -> dict:
    """Save the current run settings under a name for future sessions.
    Call this after a successful run if the user wants to save their settings.
    If files were loaded from an Excel list file, pass target_list_file/sheet/column/header_row
    instead of target_filenames — next session will re-read the file automatically."""
    sessions = _load_sessions()
    sessions[session_name] = {
        "source_root": source_root,
        "source_sheet_name": source_sheet_name,
        "header_row": header_row,
        "mode": mode,
        "target_filenames": target_filenames,
        "target_list_file": target_list_file,
        "target_list_sheet": target_list_sheet,
        "target_list_column": target_list_column,
        "target_list_header_row": target_list_header_row,
        "key_column": key_column,
        "value_column": value_column,
        "filter_column_label": filter_column_label,
        "search_term": search_term,
        "data_source_column": data_source_column,
        "master_target_column": master_target_column,
        "skip_keys": skip_keys,
        "master_id_column": master_id_column,
    }
    _save_sessions(sessions)
    return {"saved": True, "session_name": session_name, "total_sessions": len(sessions)}


@mcp.tool()
def load_target_list(file_path: str, sheet_name: str, column_name: str, header_row: int) -> dict:
    """Load the list of target filename stems from a column in an Excel file.
    The column must contain plain filename stems (e.g. '123', '999') — no extensions, no paths.
    Call this when the user provides an Excel file that contains the list of files to process.
    Returns the stems so the LLM can show them to the user before running."""
    df = source_reader.load_sheet(Path(file_path), sheet_name, header_row)
    if df is None:
        return {"error": f"Sheet '{sheet_name}' not found in '{file_path}'"}
    if column_name not in df.columns:
        return {
            "error": f"Column '{column_name}' not found",
            "available_columns": list(df.columns),
        }
    stems = [str(v) for v in df[column_name].dropna().tolist()]
    return {
        "stems": stems,
        "total": len(stems),
        "next_step": "Show the stems to the user and ask: 'Are these the files you want to process?'",
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
    Use absolute paths from list_files() for file_path."""
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
    header_row: int,
    master_id_column: str = "מספר בקשה",
    skip_keys: list[str] = [],
    master_file_path: str = "",
    conflict_resolution: str = "",
) -> dict:
    """Run mirror mode: map every row of the source sheet into the master file.
    key_column values become master column names; value_column values become the data.
    target_filenames: stems only e.g. ['123', '999'].
    skip_keys: keys to exclude.
    master_file_path: auto-generated as master_mirror.xlsx in source_root if blank.
    conflict_resolution:
      '' (default): detect conflict and ask user to choose
      'override': delete existing file, write fresh data
      'merge': keep existing file, update all cells with new data (existing rows not in this run are preserved)
      'rename': caller must supply a new master_file_path"""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_mirror.xlsx")

    if Path(master_file_path).exists() and not conflict_resolution:
        return {
            "master_file_conflict": True,
            "existing_file": master_file_path,
            "suggested_name": _suggest_name(Path(master_file_path)),
            "action": (
                "Ask the user to choose ONE option: "
                "1. Override — delete existing file and write fresh data. "
                "2. Merge — keep existing file, update cells with new data. "
                "3. Rename — provide a new file path. "
                "Then call run_mirror again with conflict_resolution='override', 'merge', or a new master_file_path."
            ),
        }

    if conflict_resolution == "override" and Path(master_file_path).exists():
        Path(master_file_path).unlink()

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
    header_row: int,
    master_id_column: str = "מספר בקשה",
    master_file_path: str = "",
    conflict_resolution: str = "",
) -> dict:
    """Run search mode: opens each target file, finds the first row where
    filter_column_label contains search_term, extracts the value from data_source_column.
    One value per file is written into master_target_column in the master file.
    This is NOT for searching across files — use list_files for file discovery.
    target_filenames: stems only e.g. ['123', '999'].
    master_file_path: auto-generated as master_search.xlsx in source_root if blank.
    conflict_resolution:
      '' (default): detect conflict and ask user to choose
      'override': delete existing file, write fresh data
      'merge': keep existing file, update all cells with new data
      'rename': caller must supply a new master_file_path"""
    if not master_file_path:
        master_file_path = str(Path(source_root) / "master_search.xlsx")

    if Path(master_file_path).exists() and not conflict_resolution:
        return {
            "master_file_conflict": True,
            "existing_file": master_file_path,
            "suggested_name": _suggest_name(Path(master_file_path)),
            "action": (
                "Ask the user to choose ONE option: "
                "1. Override — delete existing file and write fresh data. "
                "2. Merge — keep existing file, update cells with new data. "
                "3. Rename — provide a new file path. "
                "Then call run_search again with conflict_resolution='override', 'merge', or a new master_file_path."
            ),
        }

    if conflict_resolution == "override" and Path(master_file_path).exists():
        Path(master_file_path).unlink()

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
