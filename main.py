import json
import logging
import sys
from pathlib import Path

from engine.orchestrator import RunConfig, run

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "source_root",
    "target_filenames",
    "source_sheet_name",
    "filter_column_label",
    "search_term",
    "data_source_column",
    "master_target_column",
]

CONFIG_PATH = Path(__file__).parent / "config" / "run_config.json"


def load_config() -> RunConfig:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)

    missing = [k for k in REQUIRED_FIELDS if k not in data]
    if missing:
        logger.error("Missing config fields: %s", missing)
        sys.exit(1)

    if not data["target_filenames"]:
        logger.error("'target_filenames' must contain at least one entry.")
        sys.exit(1)

    if not Path(data["source_root"]).exists():
        logger.error("source_root does not exist: %s", data["source_root"])
        sys.exit(1)

    # Resolve master file path — default to master_output.xlsx inside source_root
    master_path = data.get("master_file_path", "").strip()
    if not master_path:
        master_path = str(Path(data["source_root"]) / "master_output.xlsx")
        logger.info("No master_file_path supplied. Using default: %s", master_path)

    config_kwargs = {k: data[k] for k in REQUIRED_FIELDS}
    config_kwargs["master_file_path"] = master_path
    for opt_str in ("master_id_column",):
        if opt_str in data:
            config_kwargs[opt_str] = data[opt_str]
    if "header_row" in data:
        config_kwargs["header_row"] = int(data["header_row"])
    return RunConfig(**config_kwargs)


if __name__ == "__main__":
    config = load_config()
    run(config)
