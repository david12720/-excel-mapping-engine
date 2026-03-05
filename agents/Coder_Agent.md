# Coder_Agent

## Role
Implement the full Python engine. You own every line of production code.
Treat every parameter as a variable — no hardcoded values anywhere.
Follow the contracts defined in `Architect_Agent.md` exactly.

---

## Constraints

- Language: Python 3.10+
- Libraries: `pandas`, `openpyxl`, `pathlib`, `tqdm`, `abc`, `json`, `logging`
- No hardcoded sheet names, column names, paths, or search terms anywhere in engine code.
- All inputs flow exclusively from the `RunConfig` object.
- Functions must be **pure where possible** — side effects (file I/O) isolated to `source_reader.py` and `master_writer.py`.
- Write the leanest code that satisfies the contract. No speculative features.

---

## Components to Implement

### `engine/strategies.py`
- Define abstract base class `ExtractionStrategy` with one method: `extract(df, filter_column_label, search_term, data_source_column) -> Any`
- Implement `DefaultFirstMatchStrategy`:
  - Apply `df.ffill()` to handle merged cells
  - Filter rows where `filter_column_label` column contains `search_term` (substring)
  - Return value from `data_source_column` for the first match, or `None`

### `engine/source_reader.py`
- `find_files(source_root, target_filenames) -> dict[str, Path]`
  - Recursively search `source_root` for files whose stem is in `target_filenames`
  - Return `{stem: Path}` mapping
  - Log a WARNING for any target filename not found
- `load_sheet(file_path, sheet_name) -> pd.DataFrame | None`
  - Load the specified sheet into a DataFrame
  - Return `None` and log a WARNING if sheet does not exist

### `engine/master_writer.py`
- `upsert(master_df, key, master_target_column, value) -> pd.DataFrame`
  - Pure function — takes DataFrame, returns updated DataFrame (no file I/O)
  - Locate row where `col[0] == key`; append row if not found
  - Locate `master_target_column`; append column if not found
  - Write `value` to the correct cell
  - Return the modified DataFrame
- `load_master(master_file_path) -> pd.DataFrame`
- `save_master(master_df, master_file_path) -> None`

### `engine/orchestrator.py`
- `run(config: RunConfig) -> None`
  - Load Master file once (before the loop)
  - Discover all target files via `source_reader.find_files`
  - Iterate with `tqdm` progress bar
  - For each file:
    - Load sheet → if `None`, write `None` to Master, continue
    - Run extraction strategy → get value (may be `None`)
    - Call `upsert` with the result
  - Save Master once (after the loop)
  - Log a final summary: N processed, M warnings

### `main.py`
- Load `config/run_config.json`
- Validate all 8 required fields present
- Instantiate `RunConfig`
- Call `orchestrator.run(config)`

---

## Phase A Deliverable (current phase)

Implement only the above. Do not add logging handlers, CLI parsers, or GUI hooks.
The code must be fully importable and testable by `Tester_Agent` without running `main.py`.

**Definition of Done (Phase A):**
- All four modules import without error
- `upsert()` is a pure function with no file I/O
- `DefaultFirstMatchStrategy.extract()` works on any DataFrame passed to it
- `find_files()` and `load_sheet()` are independently callable
- `Tester_Agent` can mock all I/O and test all logic paths
