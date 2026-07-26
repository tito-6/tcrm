# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from tcrm.http import request


def _post_init_hook(env):
    if request:
        request.is_frontend = False
        request.is_frontend_multilang = False
