# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import glob
import json
import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Union

import cssutils
import pandas as pd
import q2templates
from q2_types.feature_data_mag import MAGSequencesDirFmt
from q2_types.per_sample_sequences import MultiMAGSequencesDirFmt

from .types import GUNCResultsDirectoryFormat, GUNCDatabaseDirFmt

TEMPLATES = resources.files("q2_gunc") / "assets"
EXTERNAL_CMD_WARNING = (
    "Running external command line application(s). "
    "This may print messages to stdout and/or stderr.\n"
    "The command(s) being run are below. These commands "
    "cannot be manually re-run as they will depend on "
    "temporary files that no longer exist."
)


def run_command(cmd, env=None, verbose=True, **kwargs):
    """
    Run a command using subprocess, optionally printing
    the command and capturing output.

    Parameters
    ----------
    cmd : list
        Command and arguments to execute.
    env : dict, optional
        Environment variables for the subprocess.
    verbose : bool, optional
        Whether to print the command before running.
    **kwargs : dict
        Additional arguments to subprocess.run.
    """
    if verbose:
        print(EXTERNAL_CMD_WARNING)
        print("\nCommand:", end=" ")
        print(" ".join(cmd), end="\n\n")

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
        "--min_mapped_genes",
        str(min_mapped_genes),
    ]
    if sensitive:
        base_cmd.append("--sensitive")
    if use_species_level:
        base_cmd.append("--use_species_level")

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


def _run_gunc_plot(result_file: str, output_dir: str, sample_id: str = "") -> None:
    """
    Run GUNC plot command for a given result file and copy or generate the plot.

    Parameters
    ----------
    result_file : str
        Path to the result file to plot.
    output_dir : str
        Output directory for plots.
    sample_id : str, optional
        Sample identifier for organizing plots.
    """
    plots_path = Path(output_dir) / "plots" / sample_id
    os.makedirs(plots_path, exist_ok=True)
    cmd = ["gunc", "plot", "--verbose", "-d", result_file, "-o", str(plots_path)]
    run_command(cmd, verbose=True)


def _cleanup_normalize_css(css_file_path):
    """
    Removes the [type="checkbox"], [type="radio"] { ... }
    block from the CSS file using cssutils.
    """
    cssutils.log.setLevel(logging.CRITICAL)
    sheet = cssutils.parseFile(css_file_path)
    rules_to_remove = []
    for rule in sheet:
        if rule.type == rule.STYLE_RULE:
            selectors = [s.strip() for s in rule.selectorText.split(",")]
            if '[type="checkbox"]' in selectors and '[type="radio"]' in selectors:
                rules_to_remove.append(rule)
    for rule in rules_to_remove:
        sheet.deleteRule(rule)
    with open(css_file_path, "w") as f:
        f.write(sheet.cssText.decode("utf-8"))


def _process_sample(
    sample_id, sample_path, output_dir
) -> tuple[str, list[str], list[dict]]:
    """Process a single sample for visualization (used for parallelization)."""
    summary_data, sample_mags = [], []
    summary_files = list(Path(sample_path).glob("gunc_output/*.all_levels.tsv"))
    for sf in summary_files:
        df = pd.read_csv(sf, sep="\t")
        for _, row in df.iterrows():
            summary_data.append(
                {
                    "sample_id": sample_id,
                    "mag_id": row["genome"],
                    "taxonomic_level": row["taxonomic_level"],
                    "reference_representation_score": row[
                        "reference_representation_score"
                    ],
                    "contamination_portion": row["contamination_portion"],
                    "pass_gunc": bool(row["pass.GUNC"]),
                    "n_contigs": row["n_contigs"],
                    "n_genes_mapped": row["n_genes_mapped"],
                    "clade_separation_score": row["clade_separation_score"],
                    "genes_retained_index": row["genes_retained_index"],
                }
            )

    diamond_outputs = Path(sample_path) / "diamond_output"
    plots = Path(sample_path) / "plots"
    for result_file in list(diamond_outputs.glob("*")):
        mag_id = result_file.name.split(".")[0]
        sample_mags.append(mag_id)
        plot_fp = plots / f"{mag_id}.viz.html"
        if plot_fp.exists():
            dest = Path(output_dir) / "plots" / sample_id
            os.makedirs(dest, exist_ok=True)
            shutil.copy(plot_fp, dest)
        else:
            _run_gunc_plot(str(result_file), output_dir, sample_id)

    return sample_id, sample_mags, summary_data


def run_gunc(
    ctx,
    mags,
    db,
    threads=1,
    sensitive=False,
    use_species_level=False,
    min_mapped_genes=11,
    num_partitions=None,
):  # pragma: no cover
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

    (collated,) = _collate(results)

    return collated


def collate_gunc_results(
    results: GUNCResultsDirectoryFormat,
) -> GUNCResultsDirectoryFormat:
    """Collate the GUNC results."""
    output = GUNCResultsDirectoryFormat()
    for result in results:
        for sample_id, sample_path in result.file_dict().items():
            shutil.copytree(sample_path, output.path / sample_id, dirs_exist_ok=True)
    return output


def visualize(
    output_dir: str, results: GUNCResultsDirectoryFormat, threads: int = 1
) -> None:
    """Visualize the GUNC results."""
    samples = {}
    summary_data = []

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(
                _process_sample, sample_id, sample_path, output_dir
            ): sample_id
            for sample_id, sample_path in results.file_dict().items()
        }
        for future in as_completed(futures):
            sample_id, sample_mags, local_summary_data = future.result()
            samples[sample_id] = sample_mags
            summary_data.extend(local_summary_data)

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
    _cleanup_normalize_css(
        os.path.join(output_dir, "q2templateassets", "css", "normalize.css")
    )
