# ----------------------------------------------------------------------------
# Copyright (c) 2024, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from qiime2.plugin import model


class GUNCResultsFormat(model.TextFileFormat):
    def _validate_(self, level):
        pass


GUNCResultsDirectoryFormat = model.SingleFileDirectoryFormat(
    "GUNCResultsDirectoryFormat", "gunc_results.tsv", GUNCResultsFormat
)


class GUNCDatabaseDirFmt(model.DirectoryFormat):
    def _validate_(self, level):
        pass
