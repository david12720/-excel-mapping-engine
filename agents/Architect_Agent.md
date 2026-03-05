# Architect_Agent

## Role
Define the data contracts, configuration schema, and upsert logic that all other agents implement against.
Do NOT write Python. Produce specifications only.

---

## 1. Configuration Schema

Every engine run is driven by exactly 8 parameters, passed as a JSON object (loaded from `config/run_config.json`):

| Parameter            | Type        | Description                                                  |
|----------------------|-------------|--------------------------------------------------------------|
| `source_root`        | `str`       | Root directory to search recursively for source files        |
| `target_filenames`   | `list[str]` | Filename **stems** to locate (e.g. `["report", "budget"]`)  |
| `master_file_path`   | `str`       | Absolute path to the Master `.xlsx` file                     |
| `source_sheet_name`  | `str`       | Sheet name to open inside each located source file           |
| `filter_column_label`| `str`       | Column header to scan for `search_term`                      |
| `search_term`        | `str`       | Substring to find in `filter_column_label` (first match)     |
| `data_source_column` | `str`       | Column header from which the extracted value is read         |
| `master_target_column`| `str`      | Column name in the Master file where the value is written    |

### Validation Rules
- All fields are required. A missing field is a fatal config error — halt before processing any file.
- `target_filenames` must contain at least one entry.
- `source_root` and `master_file_path` must be valid filesystem paths (existence checked at startup).

---

## 2. Identity Contract

- **Key** = filename **stem** of the located source file (e.g. file `report.xlsx` → key `report`).
- Filenames are guaranteed globally unique across the entire directory tree under `source_root`.
- The key maps to a row in the Master file where **column index 0** holds matching key values.

---

## 3. Behavioral Contracts

| Scenario                          | Required Behavior                                              |
|-----------------------------------|----------------------------------------------------------------|
| `search_term` matches multiple rows | Use the **first** matching row only. Ignore subsequent matches. |
| `search_term` matches no row      | Write `None` to Master cell. Do not raise. Continue loop.      |
| `source_sheet_name` not in file   | Log a WARNING with filename. Write `None` to Master. Continue. |
| Source file not found for a target filename | Log a WARNING. Skip — do not touch the Master row.   |
| `master_target_column` absent from Master | **Create** the column (append to right). Then write.   |
| Master row for key absent         | **Create** the row (append). Set col[0] = key. Then write.    |

---

## 4. Master Upsert Contract

The upsert operation must be atomic per file — one file produces exactly one write to the Master.

**Steps (logical, not code):**
1. Load Master `.xlsx` into a DataFrame.
2. Locate row where `col[0] == key`.
   - If not found: append a new row with `col[0] = key`.
3. Locate column `master_target_column`.
   - If not found: append the column.
4. Write the extracted value to `[row_index, master_target_column]`.
5. Persist the full Master DataFrame back to `.xlsx` using the `openpyxl` engine.

---

## 5. Extraction Contract

Extraction is handled via a **Strategy interface** (`ExtractionStrategy`).

The default strategy (`DefaultFirstMatchStrategy`) must:
1. Apply `ffill()` (forward-fill) across the entire DataFrame to resolve merged cells.
2. Filter rows where `filter_column_label` contains `search_term` (case-sensitive substring).
3. Return the value at `data_source_column` for the **first** matching row.
4. Return `None` if no match.

New strategies (e.g. `LastMatchStrategy`, `RegexStrategy`) can be registered without modifying existing code — **Open/Closed Principle**.

---

## 6. Extension Points (YAGNI boundary)

The following are **not built in Phase 1** but the architecture must not block them:

- GUI frontend supplying the 8 parameters (config is already decoupled as pure JSON).
- Alternative extraction strategies (Strategy Pattern already in place).
- Async/parallel file processing (orchestrator loop is the only place concurrency would be added).
