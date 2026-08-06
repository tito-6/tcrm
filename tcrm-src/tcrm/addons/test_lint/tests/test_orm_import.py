# Part of tcrm. See LICENSE file for full copyright and licensing details.

import logging
from pathlib import Path

from tcrm.modules import Manifest
from . import lint_case
import re
_logger = logging.getLogger(__name__)

import_orm_re = re.compile(r'^(from|import)\s+tcrm\.orm')


class TestDunderinit(lint_case.LintCase):

    def test_addons_orm_import(self):
        """ Test that tcrm.orm is not imported in tcrm modules"""

        for manifest in Manifest.all_addon_manifests():
            module_path = Path(manifest.path)
            for path in module_path.rglob("**/*.py"):
                for line in path.read_text().splitlines():
                    if import_orm_re.match(line):
                        self.fail(f"Do not import directly from tcrm.orm, use tcrm.(api,fields,models): {path}")
