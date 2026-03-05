from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class ExtractionStrategy(ABC):
    @abstractmethod
    def extract(
        self,
        df: pd.DataFrame,
        filter_column_label: str,
        search_term: str,
        data_source_column: str,
    ) -> Any:
        ...


class DefaultFirstMatchStrategy(ExtractionStrategy):
    """Search mode: find first row where filter_column_label contains search_term,
    return the value from data_source_column."""

    def extract(
        self,
        df: pd.DataFrame,
        filter_column_label: str,
        search_term: str,
        data_source_column: str,
    ) -> Any:
        df = df.ffill()
        mask = df[filter_column_label].astype(str).str.contains(search_term, na=False, regex=False)
        matches = df[mask]
        if matches.empty:
            return None
        row = matches.iloc[0]
        # data_source_column can be a column name (str) or a 0-based index (int)
        if isinstance(data_source_column, int):
            return row.iloc[data_source_column]
        return row[data_source_column]


class MirrorStrategy(ExtractionStrategy):
    """Mirror mode: map every row into {key_column_value: value_column_value}.
    The returned dict is used by the orchestrator to upsert one master column per entry.
    filter_column_label = key column (A), data_source_column = value column (B).
    search_term is ignored."""

    def extract(
        self,
        df: pd.DataFrame,
        filter_column_label: str,
        search_term: str,
        data_source_column: str,
    ) -> dict[str, Any]:
        # No ffill — mirror mode expects clean explicit keys in every row.
        # Rows with a NaN/empty key are skipped.
        result = {}
        for _, row in df.iterrows():
            key = row[filter_column_label]
            if pd.notna(key) and str(key).strip():
                result[str(key)] = row[data_source_column]
        return result
