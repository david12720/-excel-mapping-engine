# Generic Excel Mapping Engine

A fully parameter-driven Python engine that extracts values from source Excel files and maps them into a Master output file.

## How It Works

1. Given a list of target filenames, the engine searches recursively under a root directory.
2. For each file found, it opens a specified sheet, locates a row by searching a label column, and extracts the value from a target column.
3. The extracted value is upserted into a Master Excel file — keyed by filename stem.

## Features

- **Zero hardcoding** — all logic is driven by `run_config.json`
- **Auto-creates Master file** if it does not exist yet
- **Handles merged cells** via `ffill()` before matching
- **Configurable header row** — works with sheets that have title rows above the actual headers
- **Column by name or index** — `data_source_column` accepts a column name (string) or a 0-based index (integer)
- **Literal string matching** — search terms are always plain text; special characters like `(`, `)` are never treated as regex
- **Strategy Pattern** — extraction logic is swappable without modifying engine code
- **25 unit tests** — all behavioral contracts are covered

## Project Structure

```
excel_mapping_engine/
├── agents/                    # Agent role definitions (architecture docs)
│   ├── Architect_Agent.md
│   ├── Coder_Agent.md
│   ├── Tester_Agent.md
│   └── Global_Orchestrator.md
├── config/
│   └── run_config.example.json   # Copy this to run_config.json and fill in values
├── engine/
│   ├── strategies.py          # ExtractionStrategy ABC + DefaultFirstMatchStrategy
│   ├── source_reader.py       # Recursive file discovery + sheet loading
│   ├── master_writer.py       # Master file upsert logic (pure function)
│   └── orchestrator.py        # Main loop + RunConfig dataclass
├── tests/                     # 25 unit tests (pytest)
├── main.py                    # Entry point
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Configuration

Copy the example config and fill in your values:

```bash
cp config/run_config.example.json config/run_config.json
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_root` | `str` | Root directory to search recursively |
| `target_filenames` | `list[str]` | Filename stems to find (e.g. `["report", "budget"]`) |
| `master_file_path` | `str` | Path to Master `.xlsx` — leave empty to auto-create |
| `master_id_column` | `str` | Name of the key column in the Master file |
| `source_sheet_name` | `str` | Sheet name to open in each source file |
| `header_row` | `int` | Row index of the header (0 = first row) |
| `filter_column_label` | `str` | Column to search for the term |
| `search_term` | `str` | Substring to find (first match wins) |
| `data_source_column` | `str\|int` | Column name or 0-based index to extract value from |
| `master_target_column` | `str` | Column name to write/create in the Master file |
| `key_column` | `str` | *(mirror)* Column whose values become master column names |
| `value_column` | `str` | *(mirror)* Column whose values become master cell values |
| `skip_keys` | `list[str]` | *(mirror, optional)* Key values to exclude — matching rows are silently skipped |

## Run

```bash
python main.py
```

## Run Tests

```bash
pytest tests/ -v
```

## Modes

### `search` (default)
Find a specific row and extract one value into a named master column.

```json
{
  "mode": "search",
  "filter_column_label": "מס' סעיף במבחנים",
  "search_term": "6(2)(א) כמות חברי גרעין",
  "data_source_column": "תוצאה",
  "master_target_column": "כמות חברי גרעין"
}
```
Result: one new column in master per run.

### `mirror`
Map **every row** of the source sheet into the master — column A values become master column names, column B values become the data.

```json
{
  "mode": "mirror",
  "key_column": "מס' סעיף במבחנים",
  "value_column": "תוצאה",
  "skip_keys": ["row to ignore", "another row"]
}
```
Result: one master column per row in the source sheet — a complete mirror of the source table. Rows whose key column value appears in `skip_keys` are silently skipped and no master column is created for them. Omit `skip_keys` (or set it to `[]`) to mirror all rows.

---

## Supported Sheet Formats

The engine is format-agnostic as long as `header_row` is set correctly. Two common layouts:

**Clean 2-column format** (recommended)
```
| מס' סעיף במבחנים          | תוצאה |
|---------------------------|-------|
| 6(2)(א) כמות חברי גרעין   | 30    |
| 5(1) ממוצע שעות התנדבות   | 111   |
```
Config: `header_row: 1`, `filter_column_label: "מס' סעיף במבחנים"`, `data_source_column: "תוצאה"`

**Legacy multi-column format** (with title rows above the header)
```
Row 0: (empty)
Row 1: תחשיב עמידה בתנאי סף :   ← title row
Row 2: מס' סעיף | תוצאה | הסבר  ← actual header
Row 3+: data...
```
Config: `header_row: 2`, `data_source_column: 4` (column index)

---

## Extending

To add a new extraction strategy (e.g. last match, regex):

```python
from engine.strategies import ExtractionStrategy

class LastMatchStrategy(ExtractionStrategy):
    def extract(self, df, filter_column_label, search_term, data_source_column):
        df = df.ffill()
        matches = df[df[filter_column_label].astype(str).str.contains(search_term, na=False)]
        if matches.empty:
            return None
        return matches.iloc[-1][data_source_column]
```

Pass it via `RunConfig(strategy=LastMatchStrategy(), ...)` — no engine code changes needed.

---

## MCP Server (LLM Interface)

`mcp_server.py` exposes the engine as 4 tools that any MCP-compatible LLM client (e.g. Claude Desktop) can call conversationally — no config file editing required.

### Setup

```bash
pip install -r requirements.txt   # installs mcp[cli]
python mcp_server.py              # starts the server
```

### Tools

| Tool | Description |
|------|-------------|
| `list_files(source_root)` | Discover all Excel files under a directory |
| `list_keys(file_path, sheet_name, key_column, header_row)` | Return available keys from a sheet |
| `run_mirror(source_root, target_filenames, source_sheet_name, key_column, value_column, master_id_column, header_row, skip_keys?, master_file_path?)` | Run mirror mode |
| `run_search(source_root, target_filenames, source_sheet_name, filter_column_label, search_term, data_source_column, master_target_column, master_id_column, header_row, master_file_path?)` | Run search mode |

`master_file_path` is auto-generated (`master_mirror.xlsx` / `master_search.xlsx` in `source_root`) if not provided. All other parameters must be supplied explicitly.
