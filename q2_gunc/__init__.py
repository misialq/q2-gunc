# flake8: noqa
# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

try:
    from ._version import __version__
except ModuleNotFoundError:
    __version__ = "0.0.0+notfound"

from .gunc import _run_gunc, run_gunc, download_gunc_db, collate_gunc_results, visualize

__all__ = [
    "_run_gunc",
    "run_gunc",
    "download_gunc_db",
    "collate_gunc_results",
    "visualize",
]
