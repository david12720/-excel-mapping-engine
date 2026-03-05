import pandas as pd
import pytest

from engine.master_writer import upsert


def make_master(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_u01_key_exists_column_exists():
    df = make_master([{"id": "alpha", "score": 0}, {"id": "beta", "score": 5}])
    result = upsert(df, "alpha", "score", 99)
    assert result.loc[result["id"] == "alpha", "score"].iloc[0] == 99
    assert result.loc[result["id"] == "beta", "score"].iloc[0] == 5  # untouched


def test_u02_key_exists_column_absent():
    df = make_master([{"id": "alpha"}, {"id": "beta"}])
    result = upsert(df, "alpha", "new_col", 42)
    assert "new_col" in result.columns
    assert result.loc[result["id"] == "alpha", "new_col"].iloc[0] == 42
    # Other rows get None in the new column
    assert result.loc[result["id"] == "beta", "new_col"].iloc[0] is None


def test_u03_key_absent_column_exists():
    df = make_master([{"id": "alpha", "score": 10}])
    result = upsert(df, "gamma", "score", 77)
    assert len(result) == 2
    assert result.loc[result["id"] == "gamma", "score"].iloc[0] == 77
    assert result.loc[result["id"] == "alpha", "score"].iloc[0] == 10  # untouched


def test_u04_key_absent_column_absent():
    df = make_master([{"id": "alpha"}])
    result = upsert(df, "gamma", "new_col", 55)
    assert len(result) == 2
    assert "new_col" in result.columns
    assert result.loc[result["id"] == "gamma", "new_col"].iloc[0] == 55


def test_u05_value_is_none():
    df = make_master([{"id": "alpha", "score": 10}])
    result = upsert(df, "alpha", "score", None)
    # pandas coerces None to NaN in numeric columns; use pd.isna() for the check
    assert pd.isna(result.loc[result["id"] == "alpha", "score"].iloc[0])


def test_u06_empty_master():
    df = pd.DataFrame(columns=["id"])
    result = upsert(df, "alpha", "score", 42)
    assert len(result) == 1
    assert result.iloc[0]["id"] == "alpha"
    assert result.iloc[0]["score"] == 42


def test_upsert_is_pure_does_not_mutate_input():
    df = make_master([{"id": "alpha", "score": 10}])
    original_value = df.loc[df["id"] == "alpha", "score"].iloc[0]
    upsert(df, "alpha", "score", 999)
    assert df.loc[df["id"] == "alpha", "score"].iloc[0] == original_value
