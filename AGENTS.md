# Agent Context — Excel Mapping Engine

Quick-reference for AI agents and future sessions. Read this before touching any code.

---

## What This Project Does

Extracts values from multiple source Excel files and upserts them into a single Master `.xlsx` file. All behaviour is driven by `config/run_config.json` — no hardcoding.

---

## Repo Layout

```
excel_mapping_engine/      ← project root (also the git root)
├── engine/
│   ├── orchestrator.py    ← RunConfig dataclass + run() main loop
│   ├── strategies.py      ← ExtractionStrategy ABC, DefaultFirstMatchStrategy, MirrorStrategy
│   ├── source_reader.py   ← file discovery + sheet loading
│   └── master_writer.py   ← upsert logic (pure function)
├── config/
│   ├── run_config.json         ← gitignored (local paths); copy of example below
│   └── run_config.example.json ← committed template
├── tests/                 ← pytest, 32 tests
├── main.py                ← entry point; reads config/run_config.json
└── README.md              ← user-facing docs
```

---

## Branch Convention

| Branch | Purpose |
|--------|---------|
| `main` | stable, merged features |
| `feature/mirror-mode` | current working branch |

Always work on a feature branch, PR into `main`.

---

## How to Run

```bash
# from excel_mapping_engine/
python main.py          # runs the engine
pytest tests/ -v        # runs all 32 tests
```

---

## Real Config Values (from owner's environment)

These are the actual field values used against real source files — agents should use these as defaults when writing or suggesting config:

| Field | Value |
|-------|-------|
| `source_root` | `C:/Users/david/Downloads/excel_repo/src_for_test` |
| `target_filenames` | `["123", "999"]` |
| `source_sheet_name` | `נספח ב` |
| `header_row` | `1` |
| `master_id_column` | `מספר בקשה` |
| `key_column` (mirror) | `מס' סעיף במבחנים` |
| `value_column` (mirror) | `תוצאה` |
| `filter_column_label` (search) | `מס' סעיף במבחנים` |
| `data_source_column` (search) | `תוצאה` |
| `master_file_path` (mirror) | `C:/Users/david/Downloads/excel_repo/master_mirror.xlsx` |
| `master_file_path` (search) | `C:/Users/david/Downloads/excel_repo/master_search.xlsx` |

Both modes share one `run_config.json` — switch by changing `"mode"` only.

---

## Key Design Decisions

- **`skip_keys` filters in orchestrator, not strategy** — `ExtractionStrategy.extract()` signature is intentionally unchanged; filtering dict results happens in `run()` after extraction.
- **Strategy pattern** — swap extraction logic via `RunConfig(strategy=...)` without touching engine code.
- **`run_config.json` is gitignored** — contains local absolute paths. Use `run_config.example.json` as the committed template.
- **Both mode configs coexist in one JSON** — unused fields are ignored by `main.py`. Only `"mode"` needs to change between runs.
- **Hebrew field names are normal** — column names in source files are Hebrew; treat them as opaque strings.
- **`master_writer.upsert` is a pure function** — always returns a new DataFrame, never mutates input.

---

## Known Source Keys (mirror mode)

All keys present in `מס' סעיף במבחנים` column of real source files:

```
6(1)(א) ניהול תקין
6(1)(ג) מטרות המוסד
6(1)(ד)(1) הפרדת דוחות כספיים
6(1)(ד)(2) פעילות עיקרית
6(2)(א) נתמך לראשונה
6(2)(א) כמות חברי גרעין
5(1) ממוצע שעות התנדבות 2025
5(1) שעות התנדבות ב2 פרויקטים
6(2)(ג) מס' נפשות
6(2)(ד) אינם תושבי רשות מקומית
6(2)(ה) מגורים דרך קבע
6(2)(ן) תכנית עבודה
6(2)(ז) מס' משתתפים תקין
6(2)(ז) ייעוד לתושבי הרשות
6(ח)(4) השתתפות 10%
5(3) רכז 70%
9(1)(א)
9(1)(ב) ותק גרעין
9(1)(ג) אחוז לא תושבי המקום
9(1)(ד) ממוצע שעות התנדבות שנת ההערכה
9(1)(ה) אחוז משרתי צבא
9(1)(ו)אסמכתא רשות מקומית
מדד כללי חברתי - רשות מקומית עיריה
מדד כללי חברתי - מועצה אזורית
מדד פרפריאלי
מדד כלכלי חברתי של אזור סטטיסטי
מספר נפשות בישוב
```

Currently skipped in mirror runs: the 3 `מדד כללי חברתי` / `מדד פרפריאלי` rows.
