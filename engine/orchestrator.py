import logging
from dataclasses import dataclass, field

from tqdm import tqdm

from engine import master_writer, source_reader
from engine.strategies import DefaultFirstMatchStrategy, ExtractionStrategy

logger = logging.getLogger(__name__)


@dataclass
class RunConfig:
    source_root: str
    target_filenames: list[str]
    source_sheet_name: str
    filter_column_label: str
    search_term: str
    data_source_column: str | int   # column name OR 0-based column index
    master_target_column: str
    master_file_path: str = ""      # empty = auto-create master_output.xlsx in source_root
    master_id_column: str = "id"    # name of the key column in the Master file
    header_row: int = 0             # row index of the header (0 = first row)
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
            value = None
        else:
            try:
                value = config.strategy.extract(
                    df,
                    config.filter_column_label,
                    config.search_term,
                    config.data_source_column,
                )
            except Exception as e:
                logger.warning("Extraction failed for '%s': %s", stem, e)
                warnings += 1
                value = None

        master_df = master_writer.upsert(master_df, stem, config.master_target_column, value)
        processed += 1

    master_writer.save_master(master_df, config.master_file_path)
    logger.info("Done. Processed: %d, Warnings: %d", processed, warnings)
