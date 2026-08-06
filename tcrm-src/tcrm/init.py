# ruff: noqa: E402, F401
# Part of tcrm. See LICENSE file for full copyright and licensing details.

""" tcrm initialization. """

import gc
import sys
from .release import MIN_PY_VERSION
assert sys.version_info > MIN_PY_VERSION, f"Outdated python version detected, tcrm requires Python >= {'.'.join(map(str, MIN_PY_VERSION))} to run."

# ----------------------------------------------------------
# Set gc thresolds if they are default, see `tcrm.tools.gc`.
# Defaults changed from (700, 10, 10) to (2000, 10, 10) in 3.13
# and the last generation was removed in 3.14.
# ----------------------------------------------------------
if gc.get_threshold()[0] in (700, 2000):
    # Handling requests can sometimes allocate over 5k new objects, let leave
    # some space before starting any collection.
    gc.set_threshold(12_000, 20, 25)

# ----------------------------------------------------------
# Import tools to patch code and libraries
# required to do as early as possible for evented and timezone
# ----------------------------------------------------------
from . import _monkeypatches
_monkeypatches.patch_init()

from .tools.gc import gc_set_timing
gc_set_timing(enable=True)

# ----------------------------------------------------------
# Shortcuts
# Expose them at the `tcrm` namespace level
# ----------------------------------------------------------
import tcrm
from .orm.commands import Command
from .orm.utils import SUPERUSER_ID
from .tools.translate import _, _lt

tcrm.SUPERUSER_ID = SUPERUSER_ID
tcrm._ = _
tcrm._lt = _lt
tcrm.Command = Command
