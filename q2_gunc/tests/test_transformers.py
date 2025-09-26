# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import pandas as pd
import qiime2
from qiime2.plugin.testing import TestPluginBase

from q2_gunc.types import (
    GUNCResultsDirectoryFormat,
)


class TestTransformers(TestPluginBase):
    package = "q2_gunc.tests"

    def setUp(self):
        super().setUp()
        self.data_no_samples = self.get_data_path("results")
        self.data_with_samples = self.get_data_path("results-per-sample")
        self.data_empty = self.get_data_path("results-empty")

    def test_gunc_to_df(self):
        transformer = self.get_transformer(GUNCResultsDirectoryFormat, pd.DataFrame)
        obs = transformer(GUNCResultsDirectoryFormat(self.data_no_samples, mode="r"))

        self.assertEqual(obs.index.name, "id")
        self.assertNotIn("sample_id", obs.columns)
        self.assertEqual(obs.shape, (14, 13))

    def test_gunc_to_df_with_samples(self):
        transformer = self.get_transformer(GUNCResultsDirectoryFormat, pd.DataFrame)
        obs = transformer(GUNCResultsDirectoryFormat(self.data_with_samples, mode="r"))

        self.assertEqual(obs.index.name, "id")
        self.assertIn("sample_id", obs.columns)
        self.assertEqual(obs.shape, (28, 14))
        self.assertSetEqual(set(obs["sample_id"]), {"SRR9640343", "SRR9640344"})

    def test_gunc_to_df_no_data(self):
        transformer = self.get_transformer(GUNCResultsDirectoryFormat, pd.DataFrame)
        with self.assertRaisesRegex(ValueError, "No GUNC results"):
            transformer(GUNCResultsDirectoryFormat(self.data_empty, mode="r"))

    def test_gunc_to_metadata(self):
        transformer = self.get_transformer(GUNCResultsDirectoryFormat, qiime2.Metadata)
        obs = transformer(GUNCResultsDirectoryFormat(self.data_no_samples, mode="r"))

        self.assertIsInstance(obs, qiime2.Metadata)

        obs = obs.to_dataframe()
        self.assertEqual(obs.index.name, "id")
        self.assertNotIn("sample_id", obs.columns)
        self.assertEqual(obs.shape, (14, 13))

    def test_gunc_to_metadata_with_samples(self):
        transformer = self.get_transformer(GUNCResultsDirectoryFormat, qiime2.Metadata)
        obs = transformer(GUNCResultsDirectoryFormat(self.data_with_samples, mode="r"))

        self.assertIsInstance(obs, qiime2.Metadata)

        obs = obs.to_dataframe()
        self.assertEqual(obs.index.name, "id")
        self.assertIn("sample_id", obs.columns)
        self.assertEqual(obs.shape, (28, 14))
        self.assertSetEqual(set(obs["sample_id"]), {"SRR9640343", "SRR9640344"})
