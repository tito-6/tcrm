# -*- coding: utf-8 -*-
import logging
import os

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import DEFAULT_BASE_URL, ZernioClient, ZernioError

_logger = logging.getLogger(__name__)


class MarketingProfile(models.Model):
    _name = 'tcrm.marketing.profile'
    _description = 'Marketing Hub Profili'
    _order = 'is_default desc, name'

    name = fields.Char(string='Ad', required=True)
    zernio_id = fields.Char(string='Zernio Profil ID', required=True, index=True, copy=False)
    is_default = fields.Boolean(string='Varsayılan')
    color = fields.Char(string='Renk')
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        required=True,
        default=lambda self: self.env.company,
    )
    account_ids = fields.One2many('tcrm.marketing.account', 'profile_id', string='Hesaplar')
    account_count = fields.Integer(compute='_compute_account_count')
    last_sync_at = fields.Datetime(string='Son Senkron')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'zernio_id_company_uniq',
            'unique(zernio_id, company_id)',
            'Bu Zernio profili bu şirket için zaten kayıtlı.',
        ),
    ]

    @api.depends('account_ids')
    def _compute_account_count(self):
        for rec in self:
            rec.account_count = len(rec.account_ids)

    @api.model
    def _get_zernio_client(self) -> ZernioClient:
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = (
            os.environ.get('ZERNIO_API_KEY')
            or ICP.get_param('tcrm_marketing_hub.zernio_api_key')
            or ''
        ).strip()
        base_url = (
            ICP.get_param('tcrm_marketing_hub.zernio_base_url') or DEFAULT_BASE_URL
        ).strip()
        if not api_key:
            raise UserError(_(
                'Zernio API anahtarı eksik. Ayarlar → Marketing Hub üzerinden ekleyin.'
            ))
        return ZernioClient(api_key=api_key, base_url=base_url)

    @api.model
    def _sync_profiles_only(self):
        """Pull Zernio profiles only (no nested Meta stack sync)."""
        try:
            client = self._get_zernio_client()
            remote_profiles = client.list_profiles()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        company = self.env.company
        Profile = self.sudo()
        synced = self.env['tcrm.marketing.profile']
        for item in remote_profiles:
            zid = item.get('_id') or item.get('id')
            if not zid:
                continue
            vals = {
                'name': item.get('name') or 'Profil',
                'zernio_id': zid,
                'is_default': bool(item.get('isDefault')),
                'color': item.get('color') or False,
                'company_id': company.id,
                'last_sync_at': fields.Datetime.now(),
            }
            existing = Profile.search([
                ('zernio_id', '=', zid),
                ('company_id', '=', company.id),
            ], limit=1)
            if existing:
                existing.write(vals)
                synced |= existing
            else:
                synced |= Profile.create(vals)

        if synced:
            default = synced.filtered('is_default')[:1] or synced[:1]
            ICP = self.env['ir.config_parameter'].sudo()
            if default and not ICP.get_param('tcrm_marketing_hub.default_profile_id'):
                ICP.set_param('tcrm_marketing_hub.default_profile_id', default.zernio_id)
        return synced

    @api.model
    def action_sync_from_zernio(self):
        """Pull profiles (+ IG/FB accounts + recent posts) from Zernio."""
        synced = self._sync_profiles_only()

        # Full Meta stack sync (best-effort; individual failures still commit profiles)
        # Campaigns last and optional — they are the slowest Zernio tree pull.
        for model_name in (
            'tcrm.marketing.account',
            'tcrm.marketing.post',
            'tcrm.marketing.ad.account',
            'tcrm.marketing.conversation',
            'tcrm.marketing.comment',
        ):
            try:
                self.env[model_name].action_sync_from_zernio()
            except Exception as exc:
                _logger.warning('Marketing Hub sync failed for %s: %s', model_name, exc)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _(
                    '%s profil + hesaplar / gelen kutusu senkronize edildi. '
                    'Kampanyalar için “Kampanyaları Çek” kullanın.'
                ) % len(synced),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_accounts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Hesaplar'),
            'res_model': 'tcrm.marketing.account',
            'view_mode': 'list,form',
            'domain': [('profile_id', '=', self.id)],
            'context': {'default_profile_id': self.id},
        }
