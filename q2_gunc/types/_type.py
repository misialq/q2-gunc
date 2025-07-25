# ----------------------------------------------------------------------------
# Copyright (c) 2025, Bokulich Lab.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from qiime2.core.type import SemanticType
from q2_types.reference_db import ReferenceDB

GUNCResults = SemanticType("GUNCResults")
GUNCDB = SemanticType("GUNCDB", variant_of=ReferenceDB.field["type"])
