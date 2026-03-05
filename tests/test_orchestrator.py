from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from engine.orchestrator import RunConfig, run


def make_config(**overrides) -> RunConfig:
    defaults = dict(
        source_root="/fake/root",
        target_filenames=["file_a", "file_b"],
        master_file_path="/fake/master.xlsx",
        source_sheet_name="Sheet1",
        filter_column_label="label",
        search_term="target",
        data_source_column="value",
        master_target_column="result_col",
    )
    defaults.update(overrides)
    return RunConfig(**defaults)


@pytest.fixture
def fake_master():
    return pd.DataFrame({"id": ["file_a", "file_b"]})


@pytest.fixture
def fake_source_df():
    return pd.DataFrame({"label": ["target"], "value": [42]})


def test_load_master_called_once(fake_master, fake_source_df):
    config = make_config()
    found_files = {"file_a": Path("/fake/root/file_a.xlsx")}

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master) as mock_load,
        patch("engine.orchestrator.master_writer.save_master") as mock_save,
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=fake_source_df),
    ):
        run(config)
        mock_load.assert_called_once_with(config.master_file_path, config.master_id_column)
        mock_save.assert_called_once()


def test_save_master_called_once_after_loop(fake_master, fake_source_df):
    config = make_config(target_filenames=["file_a", "file_b"])
    found_files = {
        "file_a": Path("/fake/root/file_a.xlsx"),
        "file_b": Path("/fake/root/file_b.xlsx"),
    }

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master),
        patch("engine.orchestrator.master_writer.save_master") as mock_save,
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=fake_source_df),
    ):
        run(config)
        assert mock_save.call_count == 1  # saved once, not per file


def test_none_written_when_sheet_missing(fake_master):
    config = make_config(target_filenames=["file_a"])
    found_files = {"file_a": Path("/fake/root/file_a.xlsx")}

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master),
        patch("engine.orchestrator.master_writer.save_master"),
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=None),
        patch("engine.orchestrator.master_writer.upsert", return_value=fake_master) as mock_upsert,
    ):
        run(config)
        mock_upsert.assert_called_once_with(
            fake_master, "file_a", config.master_target_column, None
        )


def test_none_written_when_extraction_fails(fake_master):
    config = make_config(target_filenames=["file_a"])
    found_files = {"file_a": Path("/fake/root/file_a.xlsx")}
    bad_df = pd.DataFrame({"wrong_col": [1]})  # missing filter_column_label -> KeyError

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master),
        patch("engine.orchestrator.master_writer.save_master"),
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=bad_df),
        patch("engine.orchestrator.master_writer.upsert", return_value=fake_master) as mock_upsert,
    ):
        run(config)
        mock_upsert.assert_called_once_with(
            fake_master, "file_a", config.master_target_column, None
        )


def test_correct_value_written_on_success(fake_master, fake_source_df):
    config = make_config(target_filenames=["file_a"])
    found_files = {"file_a": Path("/fake/root/file_a.xlsx")}

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master),
        patch("engine.orchestrator.master_writer.save_master"),
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=fake_source_df),
        patch("engine.orchestrator.master_writer.upsert", return_value=fake_master) as mock_upsert,
    ):
        run(config)
        mock_upsert.assert_called_once_with(
            fake_master, "file_a", config.master_target_column, 42
        )
