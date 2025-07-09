# ----------------------------------------------------------------------------
# Copyright (c) 2024, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import glob
import subprocess
from copy import deepcopy
from typing import Union

from q2_types.feature_data_mag import MAGSequencesDirFmt
from q2_types.per_sample_sequences import MultiMAGSequencesDirFmt
from q2_types.reference_db import DiamondDatabaseDirFmt

from .types import GUNCResultsDirectoryFormat, GUNCDatabaseDirFmt


EXTERNAL_CMD_WARNING = (
    "Running external command line application(s). "
    "This may print messages to stdout and/or stderr.\n"
    "The command(s) being run are below. These commands "
    "cannot be manually re-run as they will depend on "
    "temporary files that no longer exist."
)


def run_command(cmd, env=None, verbose=True, pipe=False, **kwargs):
    if verbose:
        print(EXTERNAL_CMD_WARNING)
        print("\nCommand:", end=" ")
        print(" ".join(cmd), end="\n\n")

    if pipe:
        result = subprocess.run(
            cmd, env=env, check=True, capture_output=True, text=True
        )
        return result

    if env:
        subprocess.run(cmd, env=env, check=True, **kwargs)
    else:
        subprocess.run(cmd, check=True, **kwargs)


def download_gunc_db(database: str = "progenomes") -> GUNCDatabaseDirFmt:
    """Download the GUNC reference database."""

    db = GUNCDatabaseDirFmt()
    cmd = ["gunc", "download_db", str(db.path)]
    if database:
        cmd.extend(["--database", database])

    run_command(cmd, verbose=True)
    return db


def _run_gunc(
    mags: Union[MAGSequencesDirFmt, MultiMAGSequencesDirFmt],
    db: GUNCDatabaseDirFmt,
    threads: int = 1,
    sensitive: bool = False,
    use_species_level: bool = False,
    min_mapped_genes: int = 11,
) -> GUNCResultsDirectoryFormat:
    """Run GUNC on the provided MAGs."""

    results = GUNCResultsDirectoryFormat()
    db_fp = glob.glob(f"{db.path}/*.dmnd")[0]

    base_cmd = [
        "gunc",
        "run",
        "--db_file",
        db_fp,
        "--threads",
        str(threads),
        "--file_suffix",
        ".fasta",
        "--detailed_output",
    ]
    if sensitive:
        base_cmd.append("--sensitive")
    if use_species_level:
        base_cmd.append("--use_species_level")
    if min_mapped_genes is not None:
        base_cmd.extend(["--min_mapped_genes", str(min_mapped_genes)])

    if isinstance(mags, MultiMAGSequencesDirFmt):
        for sample_id, mags in mags.sample_dict():
            cmd = deepcopy(base_cmd)
            cmd.extend(
                [
                    "--input_dir",
                    str(mags.path / sample_id),
                    "--out_dir",
                    str(results.path / sample_id),
                ]
            )
            run_command(cmd, verbose=True)
    else:
        base_cmd.extend(
            [
                "--input_dir",
                str(mags.path),
                "--out_dir",
                str(results.path),
            ]
        )
        run_command(base_cmd, verbose=True)

    return results


def run_gunc(
    ctx,
    mags,
    db,
    threads=1,
    sensitive=False,
    use_species_level=False,
    min_mapped_genes=11,
    num_partitions=None,
):
    kwargs = {
        k: v for k, v in locals().items() if k not in ["mags", "ctx", "num_partitions"]
    }

    if issubclass(mags.format, MultiMAGSequencesDirFmt):
        partition_action = "partition_sample_data_mags"
    else:
        partition_action = "partition_feature_data_mags"
    _partition = ctx.get_action("types", partition_action)
    _run = ctx.get_action("gunc", "_run_gunc")

    (partitioned_mags,) = _partition(mags, num_partitions)
    results = []
    for mag in partitioned_mags.values():
        (result,) = _run(mag, **kwargs)
        results.append(result)
