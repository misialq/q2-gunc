# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json

import pandas as pd
from bs4 import BeautifulSoup
from q2_types.feature_data import ProteinFASTAFormat
from q2_types.genome_data import OrthologFileFmt
from q2_types.reference_db import DiamondDatabaseFileFmt
from qiime2.core.exceptions import ValidationError
from qiime2.plugin import model


class GUNCResultsFormat(model.TextFileFormat):
    COLUMNS = [
        "genome",
        "n_genes_called",
        "n_genes_mapped",
        "n_contigs",
        "taxonomic_level",
        "proportion_genes_retained_in_major_clades",
        "genes_retained_index",
        "clade_separation_score",
        "contamination_portion",
        "n_effective_surplus_clades",
        "mean_hit_identity",
        "reference_representation_score",
        "pass.GUNC",
    ]

    def _validate_(self, level):
        df = pd.read_csv(str(self), sep="\t")
        if not set(self.COLUMNS) == set(df.columns):
            raise ValidationError(
                "GUNC results file does not contain expected columns."
            )


class GUNCGeneCountsFormat(model.TextFileFormat):
    def _validate_(self, level):
        try:
            with open(str(self)) as fh:
                json.load(fh)
        except json.JSONDecodeError:
            raise ValidationError("GUNC gene counts file is not valid JSON.")


class GUNCHTMLPlotFormat(model.TextFileFormat):
    def _validate_(self, level):
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                content = file.read()
                BeautifulSoup(content, "html.parser")
        except Exception as e:
            raise ValidationError(f"GUNC HTML plot is not valid HTML: {e}")


class GUNCResultsDirectoryFormat(model.DirectoryFormat):
    diamond_output = model.FileCollection(
        r"(?:.+/)?diamond_output/.*.out", format=OrthologFileFmt
    )
    gene_calls = model.FileCollection(
        r"(?:.+/)?gene_calls/.*.genecalls.faa", format=ProteinFASTAFormat
    )
    gene_counts = model.File(
        r"(?:.+/)?gene_calls/gene_counts.json", format=GUNCGeneCountsFormat
    )
    gunc_results = model.FileCollection(
        r"(?:.+/)?gunc_output/.*.all_levels.tsv", format=GUNCResultsFormat
    )
    gunc_max_css = model.File(
        r"(?:.+/)?GUNC.*.maxCSS_level.tsv", format=GUNCResultsFormat
    )
    plots = model.FileCollection(
        r"(?:.+/)?plots/.*.viz.html", format=GUNCHTMLPlotFormat, optional=True
    )

    @diamond_output.set_path_maker
    def diamond_output_path_maker(self, sample_id, mag_id):
        prefix = f"{sample_id}/" if sample_id else ""
        return f"{prefix}diamond_output/{mag_id}.out"

    @gene_calls.set_path_maker
    def gene_calls_path_maker(self, sample_id, mag_id):
        prefix = f"{sample_id}/" if sample_id else ""
        return f"{prefix}gene_calls/{mag_id}.genecalls.faa"

    @gunc_results.set_path_maker
    def gunc_results_path_maker(self, sample_id, mag_id):
        prefix = f"{sample_id}/" if sample_id else ""
        return f"{prefix}gunc_output/{mag_id}.all_levels.tsv"

    @plots.set_path_maker
    def plots_path_maker(self, sample_id, mag_id):
        prefix = f"{sample_id}/" if sample_id else ""
        return f"{prefix}plots/{mag_id}.viz.html"

    def file_dict(self):
        subdir = self.path / "gunc_output"
        if subdir.exists() and subdir.is_dir():
            return {"": str(self.path)}
        else:
            sample_dict = {}
            for sample_dir in self.path.iterdir():
                sample_dict[sample_dir.name] = str(sample_dir)
            return sample_dict


GUNCDatabaseDirFmt = model.SingleFileDirectoryFormat(
    "GUNCDatabaseDirFmt", r".+\.dmnd$", DiamondDatabaseFileFmt
)
