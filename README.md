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

## Run

```bash
python main.py
```

## Run Tests

```bash
pytest tests/ -v
```

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
