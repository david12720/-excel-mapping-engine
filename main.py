import json
import logging
import sys
from pathlib import Path

from engine.orchestrator import RunConfig, run
from engine.source_reader import load_target_list
from engine.strategies import DefaultFirstMatchStrategy, MirrorStrategy

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

COMMON_REQUIRED = ["source_root", "source_sheet_name"]
SEARCH_REQUIRED = ["filter_column_label", "search_term", "data_source_column", "master_target_column"]
MIRROR_REQUIRED = ["key_column", "value_column"]

CONFIG_PATH = Path(__file__).parent / "config" / "run_config.json"


def _resolve_target_filenames(data: dict) -> list[str]:
    """Load target filename stems from the Excel list file specified in config."""
    list_file = data.get("target_list_file", "").strip()
    sheet     = data.get("target_list_sheet", "").strip()
    column    = data.get("target_list_column", "").strip()
    hrow      = int(data.get("target_list_header_row", 0))

    if not list_file or not sheet or not column:
        logger.error(
            "Missing target file config. Set 'target_list_file', "
            "'target_list_sheet', and 'target_list_column' in run_config.json."
        )
        sys.exit(1)

    stems = load_target_list(list_file, sheet, column, hrow)
    if stems is None:
        logger.error("Failed to load target list from '%s' (sheet='%s', column='%s').", list_file, sheet, column)
        sys.exit(1)
    if not stems:
        logger.error("Target list file returned no filenames.")
        sys.exit(1)

    logger.info("Loaded %d target filenames from '%s'.", len(stems), list_file)
    return stems


def load_config() -> RunConfig:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)

    missing_common = [k for k in COMMON_REQUIRED if k not in data]
    if missing_common:
        logger.error("Missing config fields: %s", missing_common)
        sys.exit(1)

    if not Path(data["source_root"]).exists():
        logger.error("source_root does not exist: %s", data["source_root"])
        sys.exit(1)

    mode = data.get("mode", "search")
    if mode not in ("search", "mirror"):
        logger.error("Invalid mode '%s'. Must be 'search' or 'mirror'.", mode)
        sys.exit(1)

    mode_required = SEARCH_REQUIRED if mode == "search" else MIRROR_REQUIRED
    missing_mode = [k for k in mode_required if not data.get(k)]
    if missing_mode:
        logger.error("Missing fields for mode '%s': %s", mode, missing_mode)
        sys.exit(1)

    target_filenames = _resolve_target_filenames(data)

    # Resolve master file path
    master_path = data.get("master_file_path", "").strip()
    if not master_path:
        master_path = str(Path(data["source_root"]) / "master_output.xlsx")
        logger.info("No master_file_path supplied. Using default: %s", master_path)

    strategy = MirrorStrategy() if mode == "mirror" else DefaultFirstMatchStrategy()

    config_kwargs = {k: data[k] for k in COMMON_REQUIRED}
    config_kwargs["target_filenames"] = target_filenames
    config_kwargs["mode"] = mode
    config_kwargs["master_file_path"] = master_path
    config_kwargs["strategy"] = strategy

    for field in (*SEARCH_REQUIRED, *MIRROR_REQUIRED, "master_id_column"):
        if field in data:
            config_kwargs[field] = data[field]
    if "header_row" in data:
        config_kwargs["header_row"] = int(data["header_row"])
    config_kwargs["skip_keys"] = data.get("skip_keys", [])

    return RunConfig(**config_kwargs)


if __name__ == "__main__":
    config = load_config()
    run(config)
