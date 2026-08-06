# -*- coding: utf-8 -*-
from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError

MANAGED_PLATFORMS = ('instagram', 'facebook')
ADS_PLATFORMS = ('googleads', 'metaads')
ALL_SYNC_PLATFORMS = MANAGED_PLATFORMS + ADS_PLATFORMS


class MarketingAccount(models.Model):
    _name = 'tcrm.marketing.account'
    _description = 'Marketing Hub Sosyal Hesap'
    _order = 'platform, name'
    _rec_name = 'display_name'

    name = fields.Char(string='Hesap Adı', required=True)
    username = fields.Char(string='Kullanıcı Adı')
    display_name = fields.Char(string='Görünen Ad', compute='_compute_display_name', store=True)
    zernio_id = fields.Char(string='Zernio Hesap ID', required=True, index=True, copy=False)
    platform = fields.Selection(
        [
            ('instagram', 'Instagram'),
            ('facebook', 'Facebook'),
            ('googleads', 'Google Ads'),
            ('metaads', 'Meta Ads'),
            ('other', 'Diğer'),
        ],
        string='Platform',
        required=True,
        index=True,
    )
    status = fields.Selection(
        [
            ('connected', 'Bağlı'),
            ('disconnected', 'Bağlantı Kesildi'),
            ('unknown', 'Bilinmiyor'),
        ],
        string='Durum',
        default='unknown',
    )
    profile_id = fields.Many2one(
        'tcrm.marketing.profile',
        string='Profil',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='profile_id.company_id',
        store=True,
        readonly=True,
    )
    avatar_url = fields.Char(string='Avatar URL')
    follower_count = fields.Integer(string='Takipçi')
    last_sync_at = fields.Datetime(string='Son Senkron')
    active = fields.Boolean(default=True)
    sync_enabled = fields.Boolean(
        string='Sayfa senkronizasyonu aktif',
        default=True,
        help='Kapalıysa lead form / lead senkronu bu sayfayı atlar. Mevcut leadler silinmez.',
    )
    sync_error = fields.Text(
        string='Son Senkron Hatası',
        help='Son senkron hatası (gizli anahtar içermez).',
    )
    disabled_at = fields.Datetime(string='Senkron Kapatılma Zamanı', readonly=True)
    raw_json = fields.Text(string='Ham JSON', groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        (
            'zernio_id_uniq',
            'unique(zernio_id)',
            'Bu Zernio hesabı zaten kayıtlı.',
        ),
    ]

    @api.depends('name', 'username', 'platform')
    def _compute_display_name(self):
        labels = dict(self._fields['platform'].selection)
        for rec in self:
            plat = labels.get(rec.platform) or rec.platform or ''
            handle = rec.username or rec.name or ''
            rec.display_name = f'{plat}: {handle}'.strip(': ')

    def write(self, vals):
        vals = dict(vals)
        if 'sync_enabled' in vals:
            if vals['sync_enabled']:
                vals.setdefault('disabled_at', False)
            else:
                vals.setdefault('disabled_at', fields.Datetime.now())
        return super().write(vals)
    @api.model
    def action_sync_from_zernio(self):
        Profile = self.env['tcrm.marketing.profile']
        try:
            client = Profile._get_zernio_client()
        except UserError:
            raise
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        profiles = Profile.search([('company_id', '=', self.env.company.id)])
        if not profiles:
            # Lightweight profile pull (avoid recursive full sync)
            try:
                for item in client.list_profiles():
                    zid = item.get('_id') or item.get('id')
                    if not zid:
                        continue
                    Profile.sudo().create({
                        'name': item.get('name') or 'Profil',
                        'zernio_id': zid,
                        'is_default': bool(item.get('isDefault')),
                        'color': item.get('color') or False,
                        'company_id': self.env.company.id,
                        'last_sync_at': fields.Datetime.now(),
                    })
            except ZernioError as exc:
                raise UserError(str(exc)) from exc
            profiles = Profile.search([('company_id', '=', self.env.company.id)])

        profile_by_zid = {p.zernio_id: p for p in profiles}
        Account = self.sudo()
        synced = 0
        try:
            for platform in ALL_SYNC_PLATFORMS:
                for item in client.list_accounts(platform=platform):
                    zid = item.get('_id') or item.get('id')
                    if not zid:
                        continue
                    raw_profile = item.get('profileId') or item.get('profile') or {}
                    if isinstance(raw_profile, dict):
                        profile_zid = raw_profile.get('_id') or raw_profile.get('id')
                    else:
                        profile_zid = raw_profile
                    profile = profile_by_zid.get(profile_zid) if profile_zid else None
                    if not profile:
                        profile = profiles.filtered('is_default')[:1] or profiles[:1]
                    if not profile:
                        continue
                    needs_reconnect = bool(item.get('needsReconnection'))
                    is_active = item.get('isActive', item.get('enabled', True))
                    if needs_reconnect or not is_active:
                        status = 'disconnected'
                    else:
                        status = 'connected'
                    # Map unknown platforms from Zernio ads variants
                    plat = platform
                    raw_plat = (item.get('platform') or platform or '').lower()
                    if raw_plat in dict(self._fields['platform'].selection):
                        plat = raw_plat
                    vals = {
                        'name': item.get('displayName')
                        or item.get('name')
                        or item.get('username')
                        or zid,
                        'username': item.get('username') or item.get('handle') or False,
                        'zernio_id': zid,
                        'platform': plat,
                        'status': status,
                        'profile_id': profile.id,
                        'avatar_url': item.get('avatarUrl') or item.get('profilePicture') or False,
                        'follower_count': int(
                            item.get('followersCount')
                            or item.get('followers')
                            or item.get('followerCount')
                            or 0
                        ),
                        'last_sync_at': fields.Datetime.now(),
                        'raw_json': str(item)[:8000],
                        'active': True,
                    }
                    existing = Account.search([('zernio_id', '=', zid)], limit=1)
                    if existing:
                        existing.write(vals)
                    else:
                        Account.create(vals)
                    synced += 1
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('%s hesap senkronize edildi.') % synced,
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _default_profile(self):
        ICP = self.env['ir.config_parameter'].sudo()
        zid = ICP.get_param('tcrm_marketing_hub.default_profile_id')
        Profile = self.env['tcrm.marketing.profile']
        if zid:
            profile = Profile.search([
                ('zernio_id', '=', zid),
                ('company_id', '=', self.env.company.id),
            ], limit=1)
            if profile:
                return profile
        return Profile.search([
            ('company_id', '=', self.env.company.id),
        ], order='is_default desc, id', limit=1)

    @api.model
    def action_connect_instagram(self):
        return self._action_connect_platform('instagram')

    @api.model
    def action_connect_facebook(self):
        return self._action_connect_platform('facebook')

    @api.model
    def _action_connect_platform(self, platform):
        profile = self._default_profile()
        if not profile:
            self.env['tcrm.marketing.profile'].action_sync_from_zernio()
            profile = self._default_profile()
        if not profile:
            raise UserError(_(
                'Zernio profili bulunamadı. Önce Senkronize Et çalıştırın veya '
                'Ayarlar’dan profil ID girin.'
            ))
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            data = client.get_connect_url(platform, profile.zernio_id)
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        auth_url = data.get('authUrl') or data.get('url') or data.get('auth_url')
        if not auth_url:
            raise UserError(_('Zernio bağlantı URL’si alınamadı: %s') % data)
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }
