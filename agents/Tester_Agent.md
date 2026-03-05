# Tester_Agent

## Role
Validate the engine in two sequential phases.
Phase A runs immediately using synthetic data.
Phase B runs only after the user supplies real example files.

---

## Phase A — Unit Tests (no real files required)

### Scope
Test every function in the engine in isolation using mocked DataFrames and fake directory structures.

### Test File Locations
- `tests/test_strategies.py`
- `tests/test_source_reader.py`
- `tests/test_master_writer.py`
- `tests/test_orchestrator.py`

---

### Test Cases — `DefaultFirstMatchStrategy`

| ID | Scenario | Expected |
|----|----------|----------|
| S-01 | Term found in one row | Returns correct value from `data_source_column` |
| S-02 | Term found in multiple rows | Returns value from **first** match only |
| S-03 | Term not found | Returns `None` |
| S-04 | DataFrame has merged cells (NaN gaps) | `ffill()` resolves them; correct value returned |
| S-05 | `data_source_column` exists but cell is empty | Returns `None` (or `NaN`) |
| S-06 | `filter_column_label` does not exist in DataFrame | Raises `KeyError` — document expected behavior |

---

### Test Cases — `upsert()`

| ID | Scenario | Expected |
|----|----------|----------|
| U-01 | Key exists, column exists | Cell updated in-place |
| U-02 | Key exists, column absent | Column created; cell written |
| U-03 | Key absent, column exists | Row appended; cell written |
| U-04 | Key absent, column absent | Row appended; column created; cell written |
| U-05 | Value is `None` | `None` written — no error |
| U-06 | Master DataFrame is empty | Row and column both created correctly |

---

### Test Cases — `find_files()`

| ID | Scenario | Expected |
|----|----------|----------|
| F-01 | Target file exists at root level | Returned in dict |
| F-02 | Target file exists in nested subfolder | Returned in dict |
| F-03 | Target filename not found | WARNING logged; key absent from dict |
| F-04 | Two target filenames, both found | Both returned in dict |

---

### Test Cases — `load_sheet()`

| ID | Scenario | Expected |
|----|----------|----------|
| L-01 | Sheet exists | Returns DataFrame |
| L-02 | Sheet does not exist | Returns `None`; WARNING logged |

---

## Phase B — Integration Tests (requires real files from user)

### Trigger Condition
All Phase A tests pass with zero failures.

### File Request (to be filled by user)

Before running Phase B, declare the following requirements to the user:

```
I need the following example files to run integration tests:

1. Source files:
   - At least 2 .xlsx files whose stems match entries in `target_filenames`
   - Each must contain a sheet named:          ___
   - Each must contain a column named:         ___  (filter_column_label)
   - At least one row where that column has:   ___  (search_term)
   - Each must contain a column named:         ___  (data_source_column)

2. Master file:
   - 1 .xlsx file at path:                     ___
   - Column 0 must contain keys matching the source file stems

3. Explicit run parameters:
   - source_root:          ___
   - target_filenames:     ___
   - master_file_path:     ___
   - source_sheet_name:    ___
   - filter_column_label:  ___
   - search_term:          ___
   - data_source_column:   ___
   - master_target_column: ___
```

### Integration Test Cases

| ID | Scenario | Expected |
|----|----------|----------|
| I-01 | Full run with 2 valid source files | Master updated with correct values in correct cells |
| I-02 | One source file missing target sheet | Master receives `None` for that key; WARNING logged |
| I-03 | One target filename not found on disk | WARNING logged; Master row untouched for that key |
| I-04 | Run twice with same config | Master is idempotent — same result, no duplicate rows |

---

## Definition of Done

- **Phase A**: All unit test cases pass. Zero unhandled exceptions.
- **Phase B**: All integration test cases pass against real files with explicit parameters.
