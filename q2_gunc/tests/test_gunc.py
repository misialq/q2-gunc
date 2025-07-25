# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, ANY, call

from q2_types.feature_data_mag import MAGSequencesDirFmt
from q2_types.per_sample_sequences import MultiMAGSequencesDirFmt
from qiime2.plugin.testing import TestPluginBase

from q2_gunc import collate_gunc_results
from q2_gunc.gunc import GUNCResultsDirectoryFormat, GUNCDatabaseDirFmt
from q2_gunc.gunc import (
    download_gunc_db,
    _run_gunc,
    _run_gunc_plot,
    _cleanup_normalize_css,
    _process_sample,
)
from q2_gunc.gunc import visualize


class TestGUNC(TestPluginBase):
    package = "q2_gunc.tests"

    def setUp(self):
        super().setUp()
        self.mags = MAGSequencesDirFmt(self.get_data_path("mags"), mode="r")
        self.mags_per_sample = MultiMAGSequencesDirFmt(
            self.get_data_path("mags-per-sample"), mode="r"
        )
        self.db = GUNCDatabaseDirFmt(self.get_data_path("db"), mode="r")

    @patch("subprocess.run")
    def test_run_command_basic(self, subp_run):
        from q2_gunc.gunc import run_command

        run_command(["echo", "hi"], verbose=False)
        subp_run.assert_called_once_with(["echo", "hi"], check=True)

    @patch("subprocess.run")
    def test_run_command_env(self, subp_run):
        from q2_gunc.gunc import run_command

        run_command(["ls"], env={"FOO": "BAR"}, verbose=False)
        subp_run.assert_called_once_with(["ls"], env={"FOO": "BAR"}, check=True)

    @patch("subprocess.run")
    def test_download_gunc_db(self, subp_run):
        db = download_gunc_db()
        subp_run.assert_called_once_with(
            ["gunc", "download_db", str(db.path), "--database", "progenomes"],
            check=True,
        )
        self.assertIsInstance(db, GUNCDatabaseDirFmt)

    @patch("q2_gunc.gunc.run_command")
    def test_run_gunc_sample_data(self, mock_run_cmd):
        obs = _run_gunc(
            mags=self.mags_per_sample, db=self.db, threads=4, sensitive=True
        )
        exp_calls = [
            call(
                [
                    "gunc",
                    "run",
                    "--db_file",
                    str(self.db.path) + "/gtdb_95.dmnd",
                    "--threads",
                    "4",
                    "--file_suffix",
                    ".fasta",
                    "--detailed_output",
                    "--min_mapped_genes",
                    "11",
                    "--sensitive",
                    "--input_dir",
                    str(self.mags_per_sample.path) + "/sample1",
                    "--out_dir",
                    str(obs.path) + "/sample1",
                ],
                verbose=True,
            ),
            call(
                [
                    "gunc",
                    "run",
                    "--db_file",
                    str(self.db.path) + "/gtdb_95.dmnd",
                    "--threads",
                    "4",
                    "--file_suffix",
                    ".fasta",
                    "--detailed_output",
                    "--min_mapped_genes",
                    "11",
                    "--sensitive",
                    "--input_dir",
                    str(self.mags_per_sample.path) + "/sample2",
                    "--out_dir",
                    str(obs.path) + "/sample2",
                ],
                verbose=True,
            ),
        ]
        mock_run_cmd.assert_has_calls(exp_calls)
        self.assertIsInstance(obs, GUNCResultsDirectoryFormat)

    @patch("q2_gunc.gunc.run_command")
    def test_run_gunc_feature_data(self, mock_run_cmd):
        obs = _run_gunc(mags=self.mags, db=self.db, threads=4, sensitive=True)
        mock_run_cmd.assert_called_with(
            [
                "gunc",
                "run",
                "--db_file",
                str(self.db.path) + "/gtdb_95.dmnd",
                "--threads",
                "4",
                "--file_suffix",
                ".fasta",
                "--detailed_output",
                "--min_mapped_genes",
                "11",
                "--sensitive",
                "--input_dir",
                str(self.mags.path),
                "--out_dir",
                str(obs.path),
            ],
            verbose=True,
        )
        self.assertIsInstance(obs, GUNCResultsDirectoryFormat)

    @patch("q2_gunc.gunc.run_command")
    @patch("os.makedirs")
    def test_run_gunc_plot_no_sample(self, mock_makedirs, mock_run_cmd):
        _run_gunc_plot("some-results.abc", "some-output-dir")

        exp_plots_fp = Path("some-output-dir/plots")
        mock_makedirs.assert_called_once_with(exp_plots_fp, exist_ok=True)
        mock_run_cmd.assert_called_once_with(
            [
                "gunc",
                "plot",
                "--verbose",
                "-d",
                "some-results.abc",
                "-o",
                str(exp_plots_fp),
            ],
            verbose=True,
        )

    @patch("q2_gunc.gunc.run_command")
    @patch("os.makedirs")
    def test_run_gunc_plot_with_sample(self, mock_makedirs, mock_run_cmd):
        _run_gunc_plot("some-results.abc", "some-output-dir", "sample1")

        exp_plots_fp = Path("some-output-dir/plots/sample1")
        mock_makedirs.assert_called_once_with(exp_plots_fp, exist_ok=True)
        mock_run_cmd.assert_called_once_with(
            [
                "gunc",
                "plot",
                "--verbose",
                "-d",
                "some-results.abc",
                "-o",
                str(exp_plots_fp),
            ],
            verbose=True,
        )

    def test_cleanup_normalize_css(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dest = tmp.name
            shutil.copyfile(self.get_data_path("fake-normalize.css"), dest)

        _cleanup_normalize_css(dest)

        with open(dest, "r") as f:
            for _l in f.readlines():
                self.assertNotIn('[type="checkbox"]', _l)
                self.assertNotIn('[type="radio"]', _l)
        os.unlink(dest)

    @patch("shutil.copy")
    @patch("q2_gunc.gunc._run_gunc_plot")
    def test_process_sample(self, mock_plot, mock_copy):
        obs_id, obs_mags, obs_summary = _process_sample(
            "SRR9640343",
            self.get_data_path("results-per-sample/SRR9640343"),
            self.temp_dir.name,
        )

        self.assertEqual(obs_id, "SRR9640343")
        self.assertListEqual(
            sorted(obs_mags),
            [
                "0c20367d-4775-43f1-90c6-1a36afc5e4da",
                "1da59757-769b-4713-923d-e3d2e60690c9",
            ],
        )
        self.assertEqual(len(obs_summary), 14)
        mock_copy.assert_has_calls(
            [
                call(
                    Path(
                        self.get_data_path(
                            "results-per-sample/SRR9640343/plots/"
                            "1da59757-769b-4713-923d-e3d2e60690c9.viz.html"
                        )
                    ),
                    Path(self.temp_dir.name + "/plots/SRR9640343"),
                ),
                call(
                    Path(
                        self.get_data_path(
                            "results-per-sample/SRR9640343/plots/"
                            "0c20367d-4775-43f1-90c6-1a36afc5e4da.viz.html"
                        )
                    ),
                    Path(self.temp_dir.name + "/plots/SRR9640343"),
                ),
            ],
            any_order=True,
        )
        mock_plot.assert_not_called()

    @patch("shutil.copy")
    @patch("q2_gunc.gunc._run_gunc_plot")
    def test_process_sample_feature_data(self, mock_plot, mock_copy):
        obs_id, obs_mags, obs_summary = _process_sample(
            "",
            self.get_data_path("results"),
            self.temp_dir.name,
        )

        self.assertEqual(obs_id, "")
        self.assertListEqual(
            sorted(obs_mags),
            [
                "0c20367d-4775-43f1-90c6-1a36afc5e4da",
                "1da59757-769b-4713-923d-e3d2e60690c9",
            ],
        )
        self.assertEqual(len(obs_summary), 14)
        mock_copy.assert_has_calls(
            [
                call(
                    Path(
                        self.get_data_path(
                            "results/plots/"
                            "1da59757-769b-4713-923d-e3d2e60690c9.viz.html"
                        )
                    ),
                    Path(self.temp_dir.name + "/plots"),
                ),
                call(
                    Path(
                        self.get_data_path(
                            "results/plots/"
                            "0c20367d-4775-43f1-90c6-1a36afc5e4da.viz.html"
                        )
                    ),
                    Path(self.temp_dir.name + "/plots"),
                ),
            ],
            any_order=True,
        )
        mock_plot.assert_not_called()

    @patch("shutil.copy")
    @patch("q2_gunc.gunc._run_gunc_plot")
    def test_process_sample_feature_data_no_plots(self, mock_plot, mock_copy):
        obs_id, obs_mags, obs_summary = _process_sample(
            "",
            self.get_data_path("results-no-plots"),
            self.temp_dir.name,
        )

        self.assertEqual(obs_id, "")
        self.assertListEqual(
            sorted(obs_mags),
            [
                "0c20367d-4775-43f1-90c6-1a36afc5e4da",
                "1da59757-769b-4713-923d-e3d2e60690c9",
            ],
        )
        self.assertEqual(len(obs_summary), 14)
        mock_copy.assert_not_called()
        mock_plot.assert_has_calls(
            [
                call(
                    self.get_data_path(
                        "results-no-plots/diamond_output/"
                        "1da59757-769b-4713-923d-e3d2e60690c9.diamond.gtdb_95.out"
                    ),
                    self.temp_dir.name,
                    "",
                ),
                call(
                    self.get_data_path(
                        "results-no-plots/diamond_output/"
                        "0c20367d-4775-43f1-90c6-1a36afc5e4da.diamond.gtdb_95.out"
                    ),
                    self.temp_dir.name,
                    "",
                ),
            ],
            any_order=True,
        )

    @patch("q2_gunc.gunc._cleanup_normalize_css")
    @patch("os.remove")
    @patch("q2_gunc.gunc.q2templates.render")
    @patch("shutil.copytree")
    @patch("q2_gunc.gunc._process_sample")
    def test_visualize(
        self,
        mock_process_sample,
        mock_copytree,
        mock_render,
        mock_remove,
        mock_cleanup_css,
    ):
        mock_results = GUNCResultsDirectoryFormat(
            self.get_data_path("results-per-sample"), mode="r"
        )
        mock_process_sample.side_effect = [
            (
                "SRR9640343",
                ["mag1", "mag2"],
                [
                    {"sample_id": "SRR9640343", "mag_id": "mag1"},
                    {"sample_id": "SRR9640343", "mag_id": "mag2"},
                ],
            ),
            (
                "SRR9640344",
                ["mag3", "mag4"],
                [
                    {"sample_id": "SRR9640344", "mag_id": "mag3"},
                    {"sample_id": "SRR9640344", "mag_id": "mag4"},
                ],
            ),
        ]

        visualize(self.temp_dir.name, mock_results, threads=2)

        # Verify _process_sample was called for each sample
        expected_process_calls = [
            call(
                "SRR9640343",
                self.get_data_path("results-per-sample/SRR9640343"),
                self.temp_dir.name,
            ),
            call(
                "SRR9640344",
                self.get_data_path("results-per-sample/SRR9640344"),
                self.temp_dir.name,
            ),
        ]
        mock_process_sample.assert_has_calls(expected_process_calls, any_order=True)
        self.assertEqual(mock_process_sample.call_count, 2)

        # Verify JS/CSS files are copied
        expected_copytree_calls = [
            call(ANY, self.temp_dir.name + "/js"),
            call(ANY, self.temp_dir.name + "/css"),
        ]
        mock_copytree.assert_has_calls(expected_copytree_calls, any_order=True)
        self.assertEqual(mock_copytree.call_count, 2)

        # Verify template rendering
        expected_samples = {
            "SRR9640343": [
                "mag1",
                "mag2",
            ],
            "SRR9640344": [
                "mag3",
                "mag4",
            ],
        }
        expected_summary = [
            {"sample_id": "SRR9640343", "mag_id": "mag1"},
            {"sample_id": "SRR9640343", "mag_id": "mag2"},
            {"sample_id": "SRR9640344", "mag_id": "mag3"},
            {"sample_id": "SRR9640344", "mag_id": "mag4"},
        ]
        expected_context = {
            "samples": json.dumps(expected_samples),
            "summary_data": json.dumps(expected_summary),
        }
        mock_render.assert_called_once_with(
            ANY, self.temp_dir.name, context=expected_context
        )
        mock_remove.assert_called_once_with(
            self.temp_dir.name + "/q2templateassets/css/bootstrap.min.css"
        )
        mock_cleanup_css.assert_called_once_with(
            self.temp_dir.name + "/q2templateassets/css/normalize.css"
        )

    def test_collate_results(self):
        obs_result = collate_gunc_results(
            [
                GUNCResultsDirectoryFormat(
                    self.get_data_path("results-per-sample"), mode="r"
                ),
                GUNCResultsDirectoryFormat(
                    self.get_data_path("results-per-sample2"), mode="r"
                ),
            ]
        )

        self.assertIsInstance(obs_result, GUNCResultsDirectoryFormat)

        result_files = obs_result.file_dict()
        self.assertIn("SRR9640343", result_files)
        self.assertIn("SRR9640344", result_files)
        self.assertIn("SRR9640345", result_files)

        # Check that the output directories exist and contain expected files
        for sample_id in ["SRR9640343", "SRR9640344", "SRR9640345"]:
            sample_dir = result_files[sample_id]
            self.assertTrue(os.path.isdir(sample_dir))

            summary_tsv_files = [
                f for f in os.listdir(sample_dir) if f.endswith(".tsv")
            ]
            self.assertEquals(len(summary_tsv_files), 1)

            gunc_output_dir = os.path.join(sample_dir, "gunc_output")
            self.assertTrue(os.path.isdir(gunc_output_dir))

            detail_tsv_files = [
                f for f in os.listdir(gunc_output_dir) if f.endswith(".tsv")
            ]
            self.assertTrue(len(detail_tsv_files) > 0)

            diamond_output_dir = os.path.join(sample_dir, "diamond_output")
            self.assertTrue(os.path.isdir(diamond_output_dir))

            gene_calls_dir = os.path.join(sample_dir, "gene_calls")
            self.assertTrue(os.path.isdir(gene_calls_dir))
