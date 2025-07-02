# ----------------------------------------------------------------------------
# Copyright (c) 2024, Michal Ziemski.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from q2_types.feature_data import FeatureData
from q2_types.feature_data_mag import MAG
from q2_types.per_sample_sequences import MAGs
from q2_types.reference_db import ReferenceDB, Diamond
from q2_types.sample_data import SampleData
from qiime2.core.type import Range, Int, Bool, Str, Choices
from qiime2.plugin import Citations, Plugin
from q2_gunc import __version__, run_gunc, download_gunc_db
from q2_gunc.types import GUNCDB, GUNCResults, GUNCResultsFormat, GUNCResultsDirectoryFormat, GUNCDatabaseDirFmt

citations = Citations.load("citations.bib", package="q2_gunc")

plugin = Plugin(
    name="gunc",
    version=__version__,
    website="https://github.com/bokulich-lab/q2-gunc",
    package="q2_gunc",
    description="A QIIME 2 plugin for MAG analysis with GUNC.",
    short_description="Plugin for GUNC analysis.",
    # The plugin-level citation of 'Caporaso-Bolyen-2024' is provided as
    # an example. You can replace this with citations to other references
    # in citations.bib.
    citations=[citations['Caporaso-Bolyen-2024']]
)

plugin.methods.register_function(
    function=download_gunc_db,
    inputs={},
    parameters={"database": Str % Choices("progenomes", "gtdb")},
    outputs=[("db", ReferenceDB[GUNCDB])],
    input_descriptions={},
    parameter_descriptions={"database": "Which database to download."},
    output_descriptions={"db": "GUNC database."},
    name="Download GUNC database.",
    description="Download the reference database required by GUNC.",
    citations=[citations["orakov_gunc_2021"]],
)

plugin.methods.register_function(
    function=run_gunc,
    inputs={"mags": SampleData[MAGs] | FeatureData[MAG], "db": ReferenceDB[Diamond]},
    parameters={
        "threads": Int % Range(1, None),
        "sensitive": Bool,
        "detailed_output": Bool,
        "contig_taxonomy_output": Bool,
        "use_species_level": Bool,
        "min_mapped_genes": Int % Range(0, None),
    },
    outputs={"results": GUNCResults},
    input_descriptions={"mags": "MAGs to evaluate.", "db": "GUNC database."},
    parameter_descriptions={
        "threads": "Number of threads.",
        "sensitive": "Run with high sensitivity.",
        "detailed_output": "Output scores for every taxlevel.",
        "contig_taxonomy_output": "Output assignments for each contig.",
        "use_species_level": "Allow species level to be picked as maxCSS.",
        "min_mapped_genes": (
            "Dont calculate GUNC score if number of mapped genes is below this value."
        ),
    },
    output_descriptions={"results": "GUNC results table."},
    name="Detect chimerism and contamination using GUNC.",
    description="Run GUNC to evaluate MAG quality.",
    citations=[citations["orakov_gunc_2021"]],
)

plugin.register_formats(GUNCResultsFormat, GUNCResultsDirectoryFormat, GUNCDatabaseDirFmt)
plugin.register_semantic_types(GUNCResults, GUNCDB)
plugin.register_semantic_type_to_format(GUNCResults, GUNCResultsDirectoryFormat)
plugin.register_semantic_type_to_format(ReferenceDB[GUNCDB], GUNCDatabaseDirFmt)
