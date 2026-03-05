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
    def extract(
        self,
        df: pd.DataFrame,
        filter_column_label: str,
        search_term: str,
        data_source_column: str,
    ) -> Any:
        df = df.ffill()
        mask = df[filter_column_label].astype(str).str.contains(search_term, na=False)
        matches = df[mask]
        if matches.empty:
            return None
        row = matches.iloc[0]
        # data_source_column can be a column name (str) or a 0-based index (int)
        if isinstance(data_source_column, int):
            return row.iloc[data_source_column]
        return row[data_source_column]
