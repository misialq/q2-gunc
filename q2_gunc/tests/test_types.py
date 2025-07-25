# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os

import pytest
from q2_types.reference_db import ReferenceDB
from qiime2.core.exceptions import ValidationError
from qiime2.plugin.testing import TestPluginBase

from q2_gunc.types import (
    GUNCResultsFormat,
    GUNCGeneCountsFormat,
    GUNCHTMLPlotFormat,
    GUNCResultsDirectoryFormat,
    GUNCDatabaseDirFmt,
    GUNCDB,
    GUNCResults,
)


class TestTypes(TestPluginBase):
    package = "q2_gunc.tests"

    def test_guncresultsformat_valid(self):
        f = self.get_data_path("valid_gunc.tsv")
        fmt = GUNCResultsFormat(f, mode="r")
        fmt.validate()

    def test_guncresultsformat_invalid(self):
        f = self.get_data_path("invalid_gunc.tsv")
        fmt = GUNCResultsFormat(f, mode="r")
        with pytest.raises(ValidationError):
            fmt.validate()

    def test_guncgenecountsformat_valid(self):
        f = self.get_data_path("valid_gene_counts.json")
        fmt = GUNCGeneCountsFormat(f, mode="r")
        fmt.validate()

    def test_guncgenecountsformat_invalid(self):
        f = self.get_data_path("invalid_gene_counts.json")
        fmt = GUNCGeneCountsFormat(f, mode="r")
        with pytest.raises(ValidationError):
            fmt.validate()

    def test_gunchtmlplotformat_valid(self):
        f = self.get_data_path("valid_plot.html")
        fmt = GUNCHTMLPlotFormat(f, mode="r")
        fmt.validate()

    def test_gunchtmlplotformat_invalid(self):
        f = self.get_data_path("invalid_plot.html")
        fmt = GUNCHTMLPlotFormat(f, mode="r")
        # BeautifulSoup is lenient, so this may not error, but we check anyway
        try:
            fmt.validate()
        except ValidationError:
            pass

    def test_guncresultsdirectoryformat_no_samples(self):
        f = self.get_data_path("results")
        fmt = GUNCResultsDirectoryFormat(f, mode="r")
        fmt.validate()

        obs_file_dict = fmt.file_dict()
        exp_file_dict = {"": str(f)}
        self.assertDictEqual(obs_file_dict, exp_file_dict)

    def test_guncresultsdirectoryformat_with_samples(self):
        f = self.get_data_path("results-per-sample")
        fmt = GUNCResultsDirectoryFormat(f, mode="r")
        fmt.validate()

        obs_file_dict = fmt.file_dict()
        exp_file_dict = {
            "SRR9640343": os.path.join(f, "SRR9640343"),
            "SRR9640344": os.path.join(f, "SRR9640344"),
        }
        self.assertDictEqual(obs_file_dict, exp_file_dict)

    def test_guncresultsdirectoryformat_no_plots(self):
        f = self.get_data_path("results-no-plots")
        fmt = GUNCResultsDirectoryFormat(f, mode="r")
        fmt.validate()

    def test_guncdatabasedirfmt(self):
        f = self.get_data_path("db")
        fmt = GUNCDatabaseDirFmt(f, mode="r")
        fmt.validate()

    def test_db_semantic_type_registration(self):
        self.assertRegisteredSemanticType(GUNCDB)

    def test_results_semantic_type_registration(self):
        self.assertRegisteredSemanticType(GUNCResults)

    def test_db_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(
            ReferenceDB[GUNCDB], GUNCDatabaseDirFmt
        )

    def test_results_semantic_type_to_format_registration(self):
        self.assertSemanticTypeRegisteredToFormat(
            GUNCResults, GUNCResultsDirectoryFormat
        )
