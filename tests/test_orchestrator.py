from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from engine.orchestrator import RunConfig, run
from engine.strategies import MirrorStrategy


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


def test_upsert_skipped_when_extraction_fails(fake_master):
    """On extraction error the file is skipped — master is not touched."""
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
        mock_upsert.assert_not_called()


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


# ---------------------------------------------------------------------------
# Mirror mode
# ---------------------------------------------------------------------------

def make_mirror_config(**overrides) -> RunConfig:
    defaults = dict(
        source_root="/fake/root",
        target_filenames=["file_a"],
        master_file_path="/fake/master.xlsx",
        source_sheet_name="Sheet1",
        mode="mirror",
        key_column="label",
        value_column="value",
        strategy=MirrorStrategy(),
    )
    defaults.update(overrides)
    return RunConfig(**defaults)


def test_mirror_upsert_called_per_row(fake_master):
    config = make_mirror_config()
    found_files = {"file_a": Path("/fake/root/file_a.xlsx")}
    source_df = pd.DataFrame({"label": ["col_x", "col_y"], "value": [10, 20]})

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master),
        patch("engine.orchestrator.master_writer.save_master"),
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=source_df),
        patch("engine.orchestrator.master_writer.upsert", return_value=fake_master) as mock_upsert,
    ):
        run(config)
        assert mock_upsert.call_count == 2
        mock_upsert.assert_any_call(fake_master, "file_a", "col_x", 10)
        mock_upsert.assert_any_call(fake_master, "file_a", "col_y", 20)


def test_mirror_missing_sheet_does_not_touch_master(fake_master):
    config = make_mirror_config()
    found_files = {"file_a": Path("/fake/root/file_a.xlsx")}

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master),
        patch("engine.orchestrator.master_writer.save_master"),
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=None),
        patch("engine.orchestrator.master_writer.upsert", return_value=fake_master) as mock_upsert,
    ):
        run(config)
        mock_upsert.assert_not_called()


def test_mirror_skip_keys_excludes_row(fake_master):
    """M-06: skipped keys are not upserted; non-skipped keys still are."""
    config = make_mirror_config(skip_keys=["col_x"])
    found_files = {"file_a": Path("/fake/root/file_a.xlsx")}
    source_df = pd.DataFrame({"label": ["col_x", "col_y"], "value": [10, 20]})

    with (
        patch("engine.orchestrator.master_writer.load_master", return_value=fake_master),
        patch("engine.orchestrator.master_writer.save_master"),
        patch("engine.orchestrator.source_reader.find_files", return_value=found_files),
        patch("engine.orchestrator.source_reader.load_sheet", return_value=source_df),
        patch("engine.orchestrator.master_writer.upsert", return_value=fake_master) as mock_upsert,
    ):
        run(config)
        mock_upsert.assert_called_once_with(fake_master, "file_a", "col_y", 20)
        calls = [c for c in mock_upsert.call_args_list if c.args[2] == "col_x"]
        assert calls == [], "col_x should have been skipped"
