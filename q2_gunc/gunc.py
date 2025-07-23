# ----------------------------------------------------------------------------
# Copyright (c) 2024, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import glob
import json
import os
import shutil
import subprocess
import tempfile
from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Union

import q2templates
from q2_types.feature_data_mag import MAGSequencesDirFmt
from q2_types.per_sample_sequences import MultiMAGSequencesDirFmt

from .types import GUNCResultsDirectoryFormat, GUNCDatabaseDirFmt, GUNCResultsFormat

TEMPLATES = resources.files("q2_gunc") / "assets"
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
        for sample_id, _ in mags.sample_dict().items():
            cmd = deepcopy(base_cmd)
            os.makedirs(results.path / sample_id, exist_ok=True)
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
    _collate = ctx.get_action("gunc", "collate_gunc_results")

    (partitioned_mags,) = _partition(mags, num_partitions)
    results = []
    for mag in partitioned_mags.values():
        (result,) = _run(mag, **kwargs)
        results.append(result)

    collated, = _collate(results)

    return collated


def collate_gunc_results(results: GUNCResultsDirectoryFormat) -> GUNCResultsDirectoryFormat:
    """Collate the GUNC results."""
    output = GUNCResultsDirectoryFormat()
    for result in results:
        for sample_id, sample_path in result.file_dict().items():
            print(sample_id, sample_path)
            shutil.copytree(sample_path, output.path / sample_id, dirs_exist_ok=True)
    return output


def visualize(output_dir: str, results: GUNCResultsDirectoryFormat) -> None:
    """Visualize the GUNC results."""
    import pandas as pd

    samples = {}
    summary_data = []
    base_cmd = [
        "gunc", "plot", "--verbose"
    ]
    for sample_id, sample_path in results.file_dict().items():
        samples[sample_id] = []
        plots_path = Path(output_dir) / "plots" / sample_id
        os.makedirs(plots_path, exist_ok=True)
        diamond_outputs = Path(sample_path) / "diamond_output"
        
        # Read the all_levels data for this sample (includes all taxonomic levels)
        summary_files = list(Path(sample_path).glob("gunc_output/*.all_levels.tsv"))
        if summary_files:
            for sf in summary_files:
                df = pd.read_csv(sf, sep='\t')
                for _, row in df.iterrows():
                    # Convert pass.GUNC to proper boolean
                    pass_gunc_value = row['pass.GUNC']
                    if isinstance(pass_gunc_value, str):
                        pass_gunc_bool = pass_gunc_value.lower() in ['true', 'pass', '1', 'yes']
                    else:
                        pass_gunc_bool = bool(pass_gunc_value)
                    
                    summary_data.append({
                        'sample_id': sample_id,
                        'mag_id': row['genome'],
                        'taxonomic_level': row['taxonomic_level'],
                        'reference_representation_score': row['reference_representation_score'],
                        'contamination_portion': row['contamination_portion'],
                        'pass_gunc': pass_gunc_bool,
                        'n_contigs': row['n_contigs'],
                        'n_genes_mapped': row['n_genes_mapped'],
                        'clade_separation_score': row['clade_separation_score'],
                        'genes_retained_index': row['genes_retained_index']
                    })
        
        for result_file in list(diamond_outputs.glob("*")):
            mag_name = result_file.name.split('.')[0]
            samples[sample_id].append(mag_name)

            cmd = base_cmd + [
                "-d", str(result_file),
                "-o", str(plots_path)
            ]
            run_command(cmd, verbose=True)

    templates = [
        TEMPLATES / "index.html",
    ]
    context = {
        "samples": json.dumps(samples),
        "summary_data": json.dumps(summary_data),
    }

    # Copy JS/CSS files
    for d in ("js", "css"):
        shutil.copytree(TEMPLATES / d, os.path.join(output_dir, d))

    q2templates.render(templates, output_dir, context=context)

    os.remove(os.path.join(output_dir, "q2templateassets", "css", "bootstrap.min.css"))
    os.remove(os.path.join(output_dir, "q2templateassets", "css", "normalize.css"))
