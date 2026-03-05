import json
import logging
import sys
from pathlib import Path

from engine.orchestrator import RunConfig, run
from engine.strategies import DefaultFirstMatchStrategy, MirrorStrategy

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

COMMON_REQUIRED = ["source_root", "target_filenames", "source_sheet_name"]
SEARCH_REQUIRED = ["filter_column_label", "search_term", "data_source_column", "master_target_column"]
MIRROR_REQUIRED = ["key_column", "value_column"]

CONFIG_PATH = Path(__file__).parent / "config" / "run_config.json"


def load_config() -> RunConfig:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)

    missing_common = [k for k in COMMON_REQUIRED if k not in data]
    if missing_common:
        logger.error("Missing config fields: %s", missing_common)
        sys.exit(1)

    if not data["target_filenames"]:
        logger.error("'target_filenames' must contain at least one entry.")
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

    # Resolve master file path
    master_path = data.get("master_file_path", "").strip()
    if not master_path:
        master_path = str(Path(data["source_root"]) / "master_output.xlsx")
        logger.info("No master_file_path supplied. Using default: %s", master_path)

    strategy = MirrorStrategy() if mode == "mirror" else DefaultFirstMatchStrategy()

    config_kwargs = {k: data[k] for k in COMMON_REQUIRED}
    config_kwargs["mode"] = mode
    config_kwargs["master_file_path"] = master_path
    config_kwargs["strategy"] = strategy

    for field in (*SEARCH_REQUIRED, *MIRROR_REQUIRED, "master_id_column"):
        if field in data:
            config_kwargs[field] = data[field]
    if "header_row" in data:
        config_kwargs["header_row"] = int(data["header_row"])

    return RunConfig(**config_kwargs)


if __name__ == "__main__":
    config = load_config()
    run(config)
