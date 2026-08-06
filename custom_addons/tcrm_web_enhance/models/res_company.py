# -*- coding: utf-8 -*-
"""Ensure Turkish Lira (TRY) is the company / CRM default currency."""
import logging

from tcrm import api, models

_logger = logging.getLogger(__name__)


def ensure_try_currency(env):
    """
    Activate TRY and set it as currency on every company when possible.
    Returns the TRY currency record (or empty recordset).
    """
    Currency = env['res.currency'].sudo().with_context(active_test=False)
    try_cur = Currency.search([('name', '=', 'TRY')], limit=1)
    if not try_cur:
        try_cur = env.ref('base.TRY', raise_if_not_found=False)
    if not try_cur:
        _logger.warning('TCRM: TRY currency not found in res.currency')
        return Currency.browse()

    if not try_cur.active:
        try_cur.active = True

    country_tr = env.ref('base.tr', raise_if_not_found=False)
    Company = env['res.company'].sudo()
    for company in Company.search([]):
        vals = {}
        if company.currency_id != try_cur:
            vals['currency_id'] = try_cur.id
        if country_tr and company.country_id != country_tr:
            vals['country_id'] = country_tr.id
        if not vals:
            continue
        try:
            company.write(vals)
            _logger.info(
                'TCRM: company %s set to TRY / Türkiye', company.display_name
            )
        except Exception as exc:  # noqa: BLE001
            # Accounting journals may lock currency; still keep TRY active for CRM.
            _logger.warning(
                'TCRM: could not set company %s currency to TRY (%s)',
                company.display_name,
                exc,
            )
    return try_cur


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _tcrm_ensure_try_currency(self):
        return ensure_try_currency(self.env)

    def _default_currency_id(self):
        try_cur = self.env['res.currency'].sudo().with_context(
            active_test=False
        ).search([('name', '=', 'TRY')], limit=1)
        if try_cur:
            if not try_cur.active:
                try_cur.active = True
            return try_cur
        return super()._default_currency_id()

    @api.model_create_multi
    def create(self, vals_list):
        try_cur = self.env['res.currency'].sudo().with_context(
            active_test=False
        ).search([('name', '=', 'TRY')], limit=1)
        country_tr = self.env.ref('base.tr', raise_if_not_found=False)
        prepared = []
        for vals in vals_list:
            values = dict(vals)
            if try_cur and not values.get('currency_id'):
                values['currency_id'] = try_cur.id
            if country_tr and not values.get('country_id'):
                values['country_id'] = country_tr.id
            prepared.append(values)
        return super().create(prepared)
