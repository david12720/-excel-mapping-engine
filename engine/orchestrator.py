import logging
from dataclasses import dataclass, field

from tqdm import tqdm

from engine import master_writer, source_reader
from engine.strategies import DefaultFirstMatchStrategy, ExtractionStrategy, MirrorStrategy

logger = logging.getLogger(__name__)


@dataclass
class RunConfig:
    source_root: str
    target_filenames: list[str]
    source_sheet_name: str
    mode: str = "search"            # "search" or "mirror"
    # search mode params
    filter_column_label: str = ""
    search_term: str = ""
    data_source_column: str | int = ""
    master_target_column: str = ""
    # mirror mode params
    key_column: str = ""            # column A: values become master column names
    value_column: str = ""          # column B: values become master cell values
    # common optional params
    master_file_path: str = ""      # empty = auto-create master_output.xlsx in source_root
    master_id_column: str = "id"    # name of the key column in the Master file
    header_row: int = 0             # row index of the header (0 = first row)
    skip_keys: list[str] = field(default_factory=list)
    strategy: ExtractionStrategy = field(default_factory=DefaultFirstMatchStrategy)


def run(config: RunConfig) -> None:
    master_df = master_writer.load_master(config.master_file_path, config.master_id_column)
    files = source_reader.find_files(config.source_root, config.target_filenames)

    processed = 0
    warnings = 0

    for stem, path in tqdm(files.items(), desc="Processing files"):
        df = source_reader.load_sheet(path, config.source_sheet_name, config.header_row)

        if df is None:
            warnings += 1
            if config.mode == "search":
                master_df = master_writer.upsert(master_df, stem, config.master_target_column, None)
            # mirror mode: nothing to write without source data
            continue

        try:
            if config.mode == "mirror":
                value = config.strategy.extract(
                    df, config.key_column, "", config.value_column
                )
            else:
                value = config.strategy.extract(
                    df, config.filter_column_label, config.search_term, config.data_source_column
                )
        except Exception as e:
            logger.warning("Extraction failed for '%s': %s", stem, e)
            warnings += 1
            processed += 1
            continue

        if isinstance(value, dict):
            if config.skip_keys:
                skip_set = set(config.skip_keys)
                value = {k: v for k, v in value.items() if k not in skip_set}
            for col_name, col_value in value.items():
                master_df = master_writer.upsert(master_df, stem, col_name, col_value)
        else:
            master_df = master_writer.upsert(master_df, stem, config.master_target_column, value)

        processed += 1

    master_writer.save_master(master_df, config.master_file_path)
    logger.info("Done. Processed: %d, Warnings: %d", processed, warnings)
