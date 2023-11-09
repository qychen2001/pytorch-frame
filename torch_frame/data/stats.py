from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

import torch_frame
from torch_frame.typing import Series


class StatType(Enum):
    r"""The different types for column statistics.

    Attributes:
        MEAN: The average value of a numerical column.
        STD: The standard deviation of a numerical column.
        QUANTILES: The minimum, first quartile, median, third quartile,
            and the maximum of a numerical column.
        COUNT: The count of each category in a categorical column.
    """
    # Numerical:
    MEAN = 'MEAN'
    STD = 'STD'
    QUANTILES = 'QUANTILES'

    # Categorical:
    COUNT = 'COUNT'

    # Multicategorical:
    MULTI_COUNT = 'MULTI_COUNT'

    @staticmethod
    def stats_for_stype(stype: torch_frame.stype) -> List['StatType']:
        stats_type = {
            torch_frame.numerical: [
                StatType.MEAN,
                StatType.STD,
                StatType.QUANTILES,
            ],
            torch_frame.categorical: [StatType.COUNT],
            torch_frame.multicategorical: [StatType.MULTI_COUNT],
            torch_frame.sequence_numerical: [
                StatType.MEAN,
                StatType.STD,
                StatType.QUANTILES,
            ]
        }
        return stats_type.get(stype, [])

    def compute(self, ser: Series, sep: Optional[str] = None) -> Any:
        if self == StatType.MEAN:
            flattened = np.hstack(np.hstack(ser.values))
            finite_mask = np.isfinite(flattened)
            if not finite_mask.any():
                # NOTE: We may just error out here if eveything is NaN
                return np.nan
            return np.mean(flattened[finite_mask]).item()

        elif self == StatType.STD:
            flattened = np.hstack(np.hstack(ser.values))
            finite_mask = np.isfinite(flattened)
            if not finite_mask.any():
                return np.nan
            return np.std(flattened[finite_mask]).item()

        elif self == StatType.QUANTILES:
            flattened = np.hstack(np.hstack(ser.values))
            finite_mask = np.isfinite(flattened)
            if not finite_mask.any():
                return [np.nan, np.nan, np.nan, np.nan, np.nan]
            return np.quantile(
                flattened[finite_mask],
                q=[0, 0.25, 0.5, 0.75, 1],
            ).tolist()

        elif self == StatType.COUNT:
            count = ser.value_counts(ascending=False)
            return count.index.tolist(), count.values.tolist()

        elif self == StatType.MULTI_COUNT:
            assert sep is not None
            ser = ser.apply(
                lambda x: set([cat.strip() for cat in x.split(sep)])
                if (x is not None and x != '') else set())
            ser = ser.explode().dropna()
            count = ser.value_counts(ascending=False)
            return count.index.tolist(), count.values.tolist()


_default_values = {
    StatType.MEAN: np.nan,
    StatType.STD: np.nan,
    StatType.QUANTILES: [np.nan, np.nan, np.nan, np.nan, np.nan],
    StatType.COUNT: ([], []),
    StatType.MULTI_COUNT: ([], [])
}


def compute_col_stats(
    ser: Series,
    stype: torch_frame.stype,
    sep: Optional[str] = None,
) -> Dict[StatType, Any]:

    if stype == torch_frame.numerical:
        ser = ser.mask(ser.isin([np.inf, -np.inf]), np.nan)

    if ser.isnull().all():
        # NOTE: We may just error out here if eveything is NaN
        stats = {
            stat_type: _default_values[stat_type]
            for stat_type in StatType.stats_for_stype(stype)
        }
    else:
        stats = {
            stat_type: stat_type.compute(ser.dropna(), sep)
            for stat_type in StatType.stats_for_stype(stype)
        }

    return stats
