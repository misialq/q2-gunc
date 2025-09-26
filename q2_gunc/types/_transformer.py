# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import glob

import pandas as pd
import qiime2

from . import GUNCResultsDirectoryFormat
from ..plugin_setup import plugin


def _read_single_result(fp: str) -> pd.DataFrame:
    """Read a single GUNC results file into a pandas DataFrame."""
    df = pd.read_csv(fp, sep="\t", index_col=None)
    df["index"] = [f"{x}_{i}" for i, x in enumerate(df["genome"])]
    df.set_index("index", inplace=True, drop=True)
    return df


def _read_dataframes(
    fmt: GUNCResultsDirectoryFormat,
) -> pd.DataFrame:
    """Transform GUNCResultsDirectoryFormat to qiime2.Metadata.

    Parameters
    ----------
    fmt : GUNCResultsDirectoryFormat
        GUNC results directory format to read from.

    Returns
    -------
    pd.DataFrame
        pandas DataFrame with MAG IDs as index and optional sample_id column.
    """
    dataframes = []

    for sample_id, sample_fp in fmt.file_dict().items():
        for mag_fp in glob.glob(f"{sample_fp}/gunc_output/*.all_levels.tsv"):
            df = _read_single_result(mag_fp)
            if sample_id:
                df["sample_id"] = sample_id
            dataframes.append(df)

    if not dataframes:
        raise ValueError("No GUNC results found in the directory format")

    combined_df = pd.concat(dataframes)
    combined_df["pass.GUNC"] = combined_df["pass.GUNC"].astype(str)
    combined_df.index.name = "id"

    return combined_df


@plugin.register_transformer
def _1(data: GUNCResultsDirectoryFormat) -> pd.DataFrame:
    df = _read_dataframes(data)
    return df


@plugin.register_transformer
def _2(data: GUNCResultsDirectoryFormat) -> qiime2.Metadata:
    df = _read_dataframes(data)
    return qiime2.Metadata(df)
