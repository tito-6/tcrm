# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    if hasattr(env['res.company'], '_tcrm_ensure_try_currency'):
        env['res.company']._tcrm_ensure_try_currency()
    _logger.info('tcrm_web_enhance: TRY company currency migration done')
