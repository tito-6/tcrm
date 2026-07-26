# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from . import models

def _post_init_hook(env):
    _preserve_tag_on_taxes(env)

def _preserve_tag_on_taxes(env):
    from tcrm.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(env, 'l10n_lu')
