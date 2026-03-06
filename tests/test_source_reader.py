import logging

import pandas as pd
import pytest

from engine.source_reader import find_files, load_sheet, load_target_list


# ---------------------------------------------------------------------------
# find_files() — uses real tmp_path filesystem (no xlsx content needed)
# ---------------------------------------------------------------------------

def test_f01_file_at_root_level(tmp_path):
    (tmp_path / "report.xlsx").touch()
    result = find_files(str(tmp_path), ["report"])
    assert "report" in result
    assert result["report"] == tmp_path / "report.xlsx"


def test_f02_file_in_nested_subfolder(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (nested / "budget.xlsx").touch()
    result = find_files(str(tmp_path), ["budget"])
    assert "budget" in result


def test_f03_file_not_found_logs_warning(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="engine.source_reader"):
        result = find_files(str(tmp_path), ["missing_file"])
    assert "missing_file" not in result
    assert any("missing_file" in msg for msg in caplog.messages)


def test_f04_two_targets_both_found(tmp_path):
    (tmp_path / "report.xlsx").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "budget.xlsx").touch()
    result = find_files(str(tmp_path), ["report", "budget"])
    assert "report" in result
    assert "budget" in result


# ---------------------------------------------------------------------------
# load_sheet() — uses real xlsx files created in tmp_path
# ---------------------------------------------------------------------------

def _write_xlsx(path, sheet_name, df):
    df.to_excel(path, sheet_name=sheet_name, index=False, engine="openpyxl")


def test_l01_sheet_exists(tmp_path):
    path = tmp_path / "source.xlsx"
    _write_xlsx(path, "Sheet1", pd.DataFrame({"col": [1, 2, 3]}))
    result = load_sheet(path, "Sheet1")
    assert result is not None
    assert list(result.columns) == ["col"]
    assert len(result) == 3


def test_l02_sheet_missing_returns_none_and_warns(tmp_path, caplog):
    path = tmp_path / "source.xlsx"
    _write_xlsx(path, "RealSheet", pd.DataFrame({"col": [1]}))
    with caplog.at_level(logging.WARNING, logger="engine.source_reader"):
        result = load_sheet(path, "NonExistentSheet")
    assert result is None
    assert any("NonExistentSheet" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# load_target_list() — reads stems from a column in an xlsx file
# ---------------------------------------------------------------------------

def test_tl01_returns_stems_from_column(tmp_path):
    path = tmp_path / "list.xlsx"
    _write_xlsx(path, "Sheet1", pd.DataFrame({"files": ["123", "456", "789"]}))
    result = load_target_list(str(path), "Sheet1", "files", 0)
    assert result == ["123", "456", "789"]


def test_tl02_missing_sheet_returns_none(tmp_path):
    path = tmp_path / "list.xlsx"
    _write_xlsx(path, "Sheet1", pd.DataFrame({"files": ["123"]}))
    result = load_target_list(str(path), "WrongSheet", "files", 0)
    assert result is None


def test_tl03_missing_column_returns_none_and_warns(tmp_path, caplog):
    path = tmp_path / "list.xlsx"
    _write_xlsx(path, "Sheet1", pd.DataFrame({"files": ["123"]}))
    with caplog.at_level(logging.WARNING, logger="engine.source_reader"):
        result = load_target_list(str(path), "Sheet1", "wrong_col", 0)
    assert result is None
    assert any("wrong_col" in msg for msg in caplog.messages)


def test_tl04_skips_null_values(tmp_path):
    path = tmp_path / "list.xlsx"
    _write_xlsx(path, "Sheet1", pd.DataFrame({"files": ["123", None, "456"]}))
    result = load_target_list(str(path), "Sheet1", "files", 0)
    assert result == ["123", "456"]
