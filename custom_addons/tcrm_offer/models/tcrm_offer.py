# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta

from tcrm import api, fields, models, _
from tcrm.exceptions import UserError, ValidationError, AccessError

from ..services import pricing as pricing_svc
from ..services import tokens as token_svc

_logger = logging.getLogger(__name__)

PUBLIC_OPEN_STATUSES = ('published', 'viewed')
PUBLIC_READONLY_STATUSES = ('approved',)
PUBLIC_CLOSED_STATUSES = ('draft', 'paused', 'expired', 'revoked', 'closed')

ALLOWED_TRANSITIONS = {
    'draft': ('published', 'closed'),
    'published': ('viewed', 'paused', 'revoked', 'closed', 'expired', 'approved'),
    'viewed': ('approved', 'paused', 'revoked', 'closed', 'expired'),
    'paused': ('published', 'viewed', 'revoked', 'closed', 'expired'),
    'approved': ('closed',),
    'expired': ('closed',),
    'revoked': ('closed',),
    'closed': (),
}


class TcrmOffer(models.Model):
    _name = 'tcrm.offer'
    _description = 'Profesyonel Teklif'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _rec_name = 'offer_number'

    offer_number = fields.Char(
        string='Teklif No',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Yeni'),
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Müşteri', required=True, tracking=True, index=True,
    )
    partner_contact_name = fields.Char(string='Yetkili Adı')
    title = fields.Char(string='Başlık', required=True, tracking=True)
    summary = fields.Html(string='Yönetici Özeti', sanitize=True)
    scope_html = fields.Html(string='Kapsam / Hedefler', sanitize=True)
    terms_html = fields.Html(string='Ticari Şartlar', sanitize=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Para Birimi',
        required=True,
        default=lambda self: self._default_offer_currency(),
    )
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    tax_rate_snapshot = fields.Float(
        string='KDV Oranı (%)',
        digits=(16, 4),
        required=True,
        default=lambda self: float(
            self.env['ir.config_parameter'].sudo().get_param(
                'tcrm_offer.default_tax_rate', '20.0'
            )
        ),
    )
    status = fields.Selection(
        [
            ('draft', 'Taslak'),
            ('published', 'Yayında'),
            ('viewed', 'Görüntülendi'),
            ('approved', 'Onaylandı'),
            ('paused', 'Duraklatıldı'),
            ('expired', 'Süresi Doldu'),
            ('revoked', 'İptal'),
            ('closed', 'Kapalı'),
        ],
        string='Durum',
        default='draft',
        required=True,
        tracking=True,
        index=True,
        copy=False,
    )
    valid_until = fields.Date(string='Geçerlilik Tarihi', tracking=True)
    discount_amount = fields.Monetary(
        string='İndirim', currency_field='currency_id', default=0.0,
    )
    discount_reason = fields.Char(string='İndirim Nedeni')
    ad_budget_default = fields.Float(
        string='Varsayılan Reklam Bütçesi',
        digits=(16, 2),
        default=50000.0,
        help='Meta reklam bütçesi varsayılanı (müşteri seçebilir).',
    )
    ad_budget_min = fields.Float(string='Min Reklam Bütçesi', digits=(16, 2), default=0.0)
    ad_budget_max = fields.Float(string='Max Reklam Bütçesi', digits=(16, 2), default=500000.0)

    public_token_hash = fields.Char(string='Public Token Hash', copy=False, index=True)
    passcode_hash = fields.Char(string='Passcode Hash', copy=False)
    passcode_attempt_count = fields.Integer(string='Passcode Deneme', default=0, copy=False)
    locked_until = fields.Datetime(string='Kilit Bitişi', copy=False)

    # Transient plaintext shown once after generate/reset (not stored long-term intent)
    public_token_plaintext = fields.Char(
        string='Public Token (geçici)', copy=False, readonly=True,
    )
    passcode_plaintext = fields.Char(
        string='Passcode (geçici)', copy=False, readonly=True,
    )
    public_url = fields.Char(string='Public URL', compute='_compute_public_url')

    published_at = fields.Datetime(string='Yayın', copy=False)
    first_viewed_at = fields.Datetime(string='İlk Görüntülenme', copy=False)
    last_viewed_at = fields.Datetime(string='Son Görüntülenme', copy=False)
    approved_at = fields.Datetime(string='Onay', copy=False)
    closed_at = fields.Datetime(string='Kapanış', copy=False)
    revoked_at = fields.Datetime(string='İptal Zamanı', copy=False)
    paused_at = fields.Datetime(string='Duraklatma', copy=False)

    created_by = fields.Many2one(
        'res.users', string='Oluşturan',
        default=lambda self: self.env.user, readonly=True,
    )
    updated_by = fields.Many2one('res.users', string='Güncelleyen', readonly=True)
    version = fields.Integer(string='Versiyon', default=1, copy=False)

    item_ids = fields.One2many('tcrm.offer.item', 'offer_id', string='Kalemler', copy=True)
    catalogue_ids = fields.Many2many(
        'tcrm.offer.catalogue',
        'tcrm_offer_catalogue_rel',
        'offer_id',
        'catalogue_id',
        string='Açık Kataloglar',
        help='Public teklifte müşterinin görebileceği hizmet katalogları.',
    )
    provider_legal_name = fields.Char(
        string='Hizmet Sağlayıcı Unvanı',
        default='AKOD Yazılım Bilişim ve Dijital Pazarlama Ticaret Limited Şirketi',
    )
    provider_short_name = fields.Char(string='Kısa Ad', default='AKOD')
    contract_intro_html = fields.Html(
        string='Sözleşme / Teklif Giriş',
        sanitize=True,
        help='Taraflar, konu ve tanımlar gibi üst bölüm metni.',
    )
    session_ids = fields.One2many(
        'tcrm.offer.access.session', 'offer_id', string='Oturumlar',
    )
    approval_ids = fields.One2many('tcrm.offer.approval', 'offer_id', string='Onaylar')
    approval_id = fields.Many2one(
        'tcrm.offer.approval', string='Aktif Onay',
        compute='_compute_approval_id',
    )
    event_ids = fields.One2many('tcrm.offer.event', 'offer_id', string='Olaylar')

    amount_untaxed = fields.Monetary(
        string='Net Toplam', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    amount_tax = fields.Monetary(
        string='KDV', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    amount_total = fields.Monetary(
        string='Genel Toplam', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    amount_monthly = fields.Monetary(
        string='Aylık Net', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    amount_one_time = fields.Monetary(
        string='Tek Seferlik Net', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    amount_per_session = fields.Monetary(
        string='Seans Net', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )

    item_count = fields.Integer(compute='_compute_item_count')
    kvkk_url = fields.Char(
        string='KVKK URL',
        default='https://akod.tech/tr/kvkk-aydinlatma-metni',
    )
    terms_version = fields.Char(string='Şartlar Versiyonu', default='1.0')
    kvkk_version = fields.Char(string='KVKK Versiyonu', default='1.0')

    _offer_number_uniq = models.Constraint(
        'unique(offer_number)',
        'Teklif numarası benzersiz olmalıdır.',
    )

    @api.model
    def _default_offer_currency(self):
        """Teklifler her zaman TRY (TL) kullanır."""
        Currency = self.env['res.currency'].sudo().with_context(active_test=False)
        try_cur = Currency.search([('name', '=', 'TRY')], limit=1)
        if try_cur:
            if not try_cur.active:
                try_cur.active = True
            return try_cur
        return self.env.company.currency_id

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('approval_ids')
    def _compute_approval_id(self):
        for rec in self:
            rec.approval_id = rec.approval_ids[:1]

    @api.depends('item_ids')
    def _compute_item_count(self):
        for rec in self:
            rec.item_count = len(rec.item_ids)

    @api.depends('public_token_plaintext', 'public_token_hash')
    def _compute_public_url(self):
        base = self._get_public_base_url()
        for rec in self:
            token = rec.public_token_plaintext
            if token:
                rec.public_url = f'{base}/teklif/{token}'
            elif rec.public_token_hash:
                rec.public_url = f'{base}/teklif/••••••••'
            else:
                rec.public_url = False

    def _get_public_base_url(self):
        ICP = self.env['ir.config_parameter'].sudo()
        base = ICP.get_param('tcrm_offer.public_base_url') or ICP.get_param('web.base.url') or ''
        return base.rstrip('/')

    @api.depends(
        'item_ids', 'item_ids.unit_price', 'item_ids.pricing_type',
        'item_ids.billing_period', 'item_ids.selection_type',
        'item_ids.default_selected', 'item_ids.taxable',
        'item_ids.quantity', 'item_ids.custom_fee', 'item_ids.percentage_rate',
        'tax_rate_snapshot', 'ad_budget_default', 'discount_amount',
    )
    def _compute_amounts(self):
        for rec in self:
            quote = rec._quote_default_selection()
            disc = pricing_svc.to_kurus(rec.discount_amount or 0)
            net = max(0, quote['net_kurus'] - disc)
            tax_pack = pricing_svc.apply_tax(
                sum(l['net_kurus'] for l in quote['lines'] if l['taxable']) - min(
                    disc,
                    sum(l['net_kurus'] for l in quote['lines'] if l['taxable']),
                ),
                rec.tax_rate_snapshot,
            ) if quote['lines'] else {'net': 0, 'tax': 0, 'gross': 0}
            # Simpler: recompute from quote after discount on taxable portion
            rec.amount_untaxed = float(pricing_svc.from_kurus(net))
            # Apply discount proportionally for display; tax on post-discount taxable
            taxable = sum(l['net_kurus'] for l in quote['lines'] if l['taxable'])
            nontax = sum(l['net_kurus'] for l in quote['lines'] if not l['taxable'])
            taxable_after = max(0, taxable - disc)
            tax = pricing_svc.apply_tax(taxable_after, rec.tax_rate_snapshot)['tax']
            rec.amount_tax = float(pricing_svc.from_kurus(tax))
            rec.amount_total = float(pricing_svc.from_kurus(taxable_after + nontax + tax))
            rec.amount_monthly = float(pricing_svc.from_kurus(quote['monthly']['net']))
            rec.amount_one_time = float(pricing_svc.from_kurus(quote['one_time']['net']))
            rec.amount_per_session = float(pricing_svc.from_kurus(quote['per_session']['net']))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('offer_number', _('Yeni')) in (False, _('Yeni'), 'Yeni', 'New'):
                vals['offer_number'] = seq.next_by_code('tcrm.offer') or _('Yeni')
            vals.setdefault('created_by', self.env.uid)
            vals['updated_by'] = self.env.uid
            if vals.get('discount_amount') and not vals.get('discount_reason'):
                raise ValidationError(_('İndirim için neden zorunludur.'))
        records = super().create(vals_list)
        for rec in records:
            rec._log_event('created', actor_type='admin', summary=_('Teklif oluşturuldu'))
        return records

    def write(self, vals):
        vals = dict(vals)
        content_keys = {
            'title', 'summary', 'scope_html', 'terms_html', 'item_ids',
            'tax_rate_snapshot', 'valid_until', 'discount_amount', 'discount_reason',
            'partner_id', 'partner_contact_name', 'ad_budget_default',
            'ad_budget_min', 'ad_budget_max', 'currency_id',
        }
        for rec in self:
            if rec.status == 'approved' and (content_keys & set(vals)):
                raise UserError(_(
                    'Onaylanmış teklif içeriği değiştirilemez. Yeni revizyon oluşturun.'
                ))
        if vals.get('discount_amount') and not vals.get('discount_reason'):
            for rec in self:
                reason = vals.get('discount_reason') or rec.discount_reason
                if vals.get('discount_amount') and not reason:
                    raise ValidationError(_('İndirim için neden zorunludur.'))
        vals['updated_by'] = self.env.uid
        if content_keys & set(vals):
            # bump version per record via SQL-safe write
            for rec in self:
                super(TcrmOffer, rec).write({**vals, 'version': rec.version + 1})
            return True
        return super().write(vals)

    # ------------------------------------------------------------------
    # Pricing helpers
    # ------------------------------------------------------------------
    def _items_as_dicts(self):
        self.ensure_one()
        return [item._as_pricing_dict() for item in self.item_ids.filtered('active')]

    def _quote_default_selection(self):
        self.ensure_one()
        items = self._items_as_dicts()
        selected = {
            i['id'] for i in items
            if i['required'] or self.item_ids.browse(i['id']).default_selected
        }
        budget = pricing_svc.to_kurus(self.ad_budget_default or 0)
        return pricing_svc.quote_offer(
            items, selected,
            tax_rate_percent=self.tax_rate_snapshot,
            ad_budget_kurus=budget,
        )

    def action_preview_quote(self, selected_ids=None, ad_budget=None):
        self.ensure_one()
        items = self._items_as_dicts()
        if selected_ids is None:
            selected_ids = {
                i['id'] for i in items
                if i['required'] or self.item_ids.browse(i['id']).default_selected
            }
        else:
            selected_ids = set(selected_ids)
        budget = pricing_svc.to_kurus(
            ad_budget if ad_budget is not None else (self.ad_budget_default or 0)
        )
        quote = pricing_svc.quote_offer(
            items, selected_ids,
            tax_rate_percent=self.tax_rate_snapshot,
            ad_budget_kurus=budget,
        )
        disc = pricing_svc.to_kurus(self.discount_amount or 0)
        if disc:
            taxable = sum(l['net_kurus'] for l in quote['lines'] if l['taxable'])
            nontax = sum(l['net_kurus'] for l in quote['lines'] if not l['taxable'])
            taxable_after = max(0, taxable - disc)
            tax = pricing_svc.apply_tax(taxable_after, self.tax_rate_snapshot)['tax']
            quote['net_kurus'] = taxable_after + nontax
            quote['tax_kurus'] = tax
            quote['gross_kurus'] = quote['net_kurus'] + tax
            quote['discount_kurus'] = disc
        return quote

    # ------------------------------------------------------------------
    # Events / notifications
    # ------------------------------------------------------------------
    def _log_event(self, event_type, actor_type='admin', summary=None, metadata=None):
        Event = self.env['tcrm.offer.event'].sudo()
        for rec in self:
            Event.create({
                'offer_id': rec.id,
                'event_type': event_type,
                'actor_type': actor_type,
                'actor_user_id': self.env.user.id if actor_type == 'admin' else False,
                'summary': summary or event_type,
                'metadata_json': json.dumps(metadata or {}, ensure_ascii=False),
            })

    def _notify_admin(self, subject, body):
        self.ensure_one()
        try:
            self.message_post(
                body=body,
                subject=subject,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            if self.created_by:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=self.created_by.id,
                    summary=subject,
                    note=body,
                )
        except Exception:  # noqa: BLE001 — never break approval flow
            _logger.exception('Offer admin notification failed for %s', self.offer_number)

    # ------------------------------------------------------------------
    # Token / passcode
    # ------------------------------------------------------------------
    def _token_pepper(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'tcrm_offer.token_pepper', ''
        )

    def _crypt_context(self):
        return self.env.user._crypt_context()

    def _generate_credentials(self):
        self.ensure_one()
        token = token_svc.generate_public_token()
        passcode = token_svc.generate_passcode(7)
        self.write({
            'public_token_hash': token_svc.hash_token(token, pepper=self._token_pepper()),
            'passcode_hash': self._crypt_context().hash(passcode),
            'public_token_plaintext': token,
            'passcode_plaintext': passcode,
            'passcode_attempt_count': 0,
            'locked_until': False,
        })
        return token, passcode

    def action_reset_passcode(self):
        self._check_manager()
        for rec in self:
            if rec.status in ('closed', 'revoked', 'approved'):
                raise UserError(_('Bu durumda passcode yenilenemez.'))
            passcode = token_svc.generate_passcode(7)
            rec.write({
                'passcode_hash': rec._crypt_context().hash(passcode),
                'passcode_plaintext': passcode,
                'passcode_attempt_count': 0,
                'locked_until': False,
            })
            rec._log_event('passcode_reset', summary=_('Passcode yenilendi'))
        return True

    def action_copy_public_link(self):
        self.ensure_one()
        if not self.public_token_plaintext:
            raise UserError(_(
                'Public token yalnızca oluşturma/yayın anında görüntülenebilir. '
                'Yeni token için yeniden yayınlayın veya passcode sıfırlayın.'
            ))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Public Link'),
                'message': self.public_url,
                'sticky': True,
                'type': 'success',
            },
        }

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _check_manager(self):
        if not self.env.user.has_group('tcrm_offer.group_offer_manager'):
            raise AccessError(_('Bu işlem için Teklif Yöneticisi yetkisi gerekir.'))

    def _transition(self, new_status):
        for rec in self:
            allowed = ALLOWED_TRANSITIONS.get(rec.status, ())
            if new_status not in allowed:
                raise UserError(_(
                    'Geçersiz durum geçişi: %(old)s → %(new)s'
                ) % {'old': rec.status, 'new': new_status})

    def _validate_for_publish(self):
        self.ensure_one()
        if not self.item_ids:
            raise UserError(_('Yayınlamak için en az bir hizmet kalemi ekleyin.'))
        if not self.valid_until:
            raise UserError(_('Geçerlilik tarihi zorunludur.'))
        if not self.title or not self.partner_id:
            raise UserError(_('Başlık ve müşteri zorunludur.'))
        for item in self.item_ids:
            if item.pricing_type == 'meta_budget':
                budget = pricing_svc.to_kurus(self.ad_budget_default or 0)
                if pricing_svc.meta_requires_custom_fee(budget) and not item.custom_fee:
                    raise UserError(_(
                        'Meta bütçe 500.000 TL üzeri için özel yönetim ücreti girilmelidir: %s'
                    ) % item.name)
            if item.pricing_type in ('fixed', 'quantity', 'custom') and (item.unit_price or 0) <= 0:
                if item.selection_type == 'required':
                    raise UserError(_('Zorunlu kalem fiyatı eksik: %s') % item.name)

    def action_publish(self):
        self._check_manager()
        for rec in self:
            rec._validate_for_publish()
            if rec.status == 'draft':
                rec._transition('published')
            elif rec.status == 'paused':
                # reopen path uses action_reopen
                raise UserError(_('Duraklatılmış teklif için Yeniden Aç kullanın.'))
            else:
                raise UserError(_('Yalnızca taslak teklifler yayınlanabilir.'))
            token, passcode = rec._generate_credentials()
            rec.write({
                'status': 'published',
                'published_at': fields.Datetime.now(),
            })
            rec._log_event('published', summary=_('Teklif yayınlandı'))
            rec.message_post(
                body=_(
                    'Teklif yayınlandı.<br/>Public link: %s<br/>Passcode: %s<br/>'
                    '<em>Passcode yalnızca bu kez gösterilir.</em>'
                ) % (rec.public_url, passcode),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_pause(self):
        self._check_manager()
        for rec in self:
            rec._transition('paused')
            rec.write({'status': 'paused', 'paused_at': fields.Datetime.now()})
            rec.session_ids.filtered(lambda s: not s.revoked).action_revoke()
            rec._log_event('paused', summary=_('Teklif duraklatıldı'))
        return True

    def action_reopen(self):
        self._check_manager()
        for rec in self:
            if rec.status != 'paused':
                raise UserError(_('Yalnızca duraklatılmış teklifler yeniden açılabilir.'))
            target = 'viewed' if rec.first_viewed_at else 'published'
            rec._transition(target)
            rec.write({'status': target, 'paused_at': False})
            rec._log_event('reopened', summary=_('Teklif yeniden açıldı'))
        return True

    def action_revoke(self):
        self._check_manager()
        for rec in self:
            rec._transition('revoked')
            rec.write({'status': 'revoked', 'revoked_at': fields.Datetime.now()})
            rec.session_ids.filtered(lambda s: not s.revoked).action_revoke()
            rec._log_event('revoked', summary=_('Link iptal edildi'))
        return True

    def action_close(self):
        self._check_manager()
        for rec in self:
            if rec.status == 'closed':
                continue
            # Allow close from most states via explicit check
            if rec.status not in ALLOWED_TRANSITIONS or 'closed' not in ALLOWED_TRANSITIONS.get(rec.status, ()):
                # force close from draft etc. already allowed
                if rec.status == 'draft':
                    pass
                else:
                    raise UserError(_('Bu durumdan kapatılamaz: %s') % rec.status)
            rec.write({'status': 'closed', 'closed_at': fields.Datetime.now()})
            rec.session_ids.filtered(lambda s: not s.revoked).action_revoke()
            rec._log_event('closed', summary=_('Teklif kapatıldı'))
        return True

    def action_duplicate(self):
        self.ensure_one()
        copy = self.copy({
            'title': _('%s (Kopya)') % self.title,
            'status': 'draft',
            'public_token_hash': False,
            'passcode_hash': False,
            'public_token_plaintext': False,
            'passcode_plaintext': False,
            'published_at': False,
            'first_viewed_at': False,
            'last_viewed_at': False,
            'approved_at': False,
            'closed_at': False,
            'revoked_at': False,
            'paused_at': False,
            'version': 1,
        })
        self._log_event('duplicated', summary=_('Teklif çoğaltıldı → %s') % copy.offer_number)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tcrm.offer',
            'res_id': copy.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @api.model
    def _find_by_public_token(self, token):
        if not token:
            return self.browse()
        pepper = self.env['ir.config_parameter'].sudo().get_param(
            'tcrm_offer.token_pepper', ''
        )
        thash = token_svc.hash_token(token, pepper=pepper)
        return self.sudo().search([('public_token_hash', '=', thash)], limit=1)

    def public_is_accessible(self):
        self.ensure_one()
        if self.status in PUBLIC_CLOSED_STATUSES:
            return False
        if self.valid_until and self.valid_until < fields.Date.context_today(self):
            return False
        return self.status in PUBLIC_OPEN_STATUSES + PUBLIC_READONLY_STATUSES

    def public_is_selectable(self):
        self.ensure_one()
        return self.status in PUBLIC_OPEN_STATUSES and self.public_is_accessible()

    def verify_passcode(self, passcode, ip=None):
        self.ensure_one()
        now = fields.Datetime.now()
        if self.locked_until and self.locked_until > now:
            return False
        ok = False
        try:
            ok = self._crypt_context().verify(passcode or '', self.passcode_hash or '')
        except Exception:  # noqa: BLE001
            ok = False
        if ok:
            self.sudo().write({'passcode_attempt_count': 0, 'locked_until': False})
            return True
        attempts = self.passcode_attempt_count + 1
        lock_vals = {'passcode_attempt_count': attempts}
        # progressive lock: 5+ attempts → 5 min, 10+ → 30 min
        if attempts >= 10:
            lock_vals['locked_until'] = now + timedelta(minutes=30)
        elif attempts >= 5:
            lock_vals['locked_until'] = now + timedelta(minutes=5)
        self.sudo().write(lock_vals)
        self._log_event(
            'passcode_failed',
            actor_type='public',
            summary=_('Passcode başarısız'),
            metadata={'ip': token_svc.mask_ip(ip), 'attempts': attempts},
        )
        return False

    def mark_viewed(self, ip=None):
        self.ensure_one()
        vals = {'last_viewed_at': fields.Datetime.now()}
        first = False
        if self.status == 'published':
            vals['status'] = 'viewed'
            first = True
        if not self.first_viewed_at:
            vals['first_viewed_at'] = fields.Datetime.now()
            first = True
        self.sudo().write(vals)
        self._log_event('viewed', actor_type='public', summary=_('Teklif görüntülendi'),
                        metadata={'ip': token_svc.mask_ip(ip)})
        if first:
            self._notify_admin(
                _('Teklif görüntülendi: %s') % self.offer_number,
                _('Müşteri teklifi ilk kez görüntüledi: %s — %s') % (
                    self.partner_id.display_name, self.title,
                ),
            )

    def create_access_session(self, ip=None, user_agent=None, hours=12):
        self.ensure_one()
        raw = token_svc.generate_session_token()
        now = fields.Datetime.now()
        self.env['tcrm.offer.access.session'].sudo().create({
            'offer_id': self.id,
            'session_token_hash': token_svc.hash_session_token(raw),
            'authenticated_at': now,
            'expires_at': now + timedelta(hours=hours),
            'last_seen_at': now,
            'ip_masked': token_svc.mask_ip(ip),
            'user_agent': (user_agent or '')[:255],
        })
        return raw

    def get_public_payload(self):
        """Safe public JSON (no admin notes / internal costs)."""
        self.ensure_one()
        items = []
        for item in self.item_ids.filtered('active').sorted('sort_order'):
            choice_opts = []
            if item.client_choice_options:
                choice_opts = [o.strip() for o in item.client_choice_options.split(',') if o.strip()]
            items.append({
                'id': item.id,
                'name': item.name,
                'description': item.description or '',
                'category': item.category or '',
                'pricing_type': item.pricing_type,
                'unit_price': item.unit_price,
                'billing_period': item.billing_period,
                'selection_type': item.selection_type,
                'default_selected': item.default_selected or item.selection_type == 'required',
                'taxable': item.taxable,
                'includes_html': item.includes_html or '',
                'excludes_html': item.excludes_html or '',
                'exclusive_group': item.exclusive_group or '',
                'quantity': item.quantity,
                'code': item.code or '',
                'package_group': item.package_group or 'optional',
                'client_choice_label': item.client_choice_label or '',
                'client_choice_options': choice_opts,
            })
        catalogues = []
        for cat in self.catalogue_ids.filtered('active').sorted('sequence'):
            catalogues.append({
                'id': cat.id,
                'name': cat.name,
                'code': cat.code,
                'summary': cat.summary or '',
                'items': [{
                    'name': ci.name,
                    'description': ci.description or '',
                    'price_from': ci.price_from,
                    'price_to': ci.price_to,
                    'price_note': ci.price_note or '',
                    'billing_period': ci.billing_period,
                    'highlight': ci.highlight,
                } for ci in cat.item_ids.sorted('sort_order')],
            })
        return {
            'offer_number': self.offer_number,
            'title': self.title,
            'partner_name': self.partner_id.name,
            'partner_contact_name': self.partner_contact_name or '',
            'provider_legal_name': self.provider_legal_name or 'AKOD',
            'provider_short_name': self.provider_short_name or 'AKOD',
            'summary': self.summary or '',
            'scope_html': self.scope_html or '',
            'terms_html': self.terms_html or '',
            'contract_intro_html': self.contract_intro_html or '',
            'valid_until': fields.Date.to_string(self.valid_until) if self.valid_until else '',
            'tax_rate': self.tax_rate_snapshot,
            'currency': self.currency_id.name,
            'status': self.status,
            'ad_budget_default': self.ad_budget_default,
            'ad_budget_min': self.ad_budget_min,
            'ad_budget_max': self.ad_budget_max,
            'kvkk_url': self.kvkk_url,
            'terms_version': self.terms_version,
            'kvkk_version': self.kvkk_version,
            'selectable': self.public_is_selectable(),
            'items': items,
            'catalogues': catalogues,
            'approved': bool(self.approval_id),
        }

    def action_approve_public(
        self,
        *,
        selected_ids,
        ad_budget,
        approver_name,
        approver_email,
        approver_company=None,
        approver_phone=None,
        accepted_services=False,
        accepted_terms=False,
        accepted_kvkk=False,
        idempotency_key=None,
        ip=None,
        user_agent=None,
    ):
        self.ensure_one()
        offer = self.sudo()
        Approval = offer.env['tcrm.offer.approval']

        # Idempotent / already-approved short-circuit before state checks
        if idempotency_key:
            existing = Approval.search([('idempotency_key', '=', idempotency_key)], limit=1)
            if existing:
                return existing
        if offer.approval_ids:
            return offer.approval_ids[:1]

        if offer.valid_until and offer.valid_until < fields.Date.context_today(offer):
            if offer.status in PUBLIC_OPEN_STATUSES:
                offer.write({'status': 'expired'})
        if not offer.public_is_selectable():
            raise UserError(_('Bu teklif onaylanamaz.'))
        if not (accepted_services and accepted_terms and accepted_kvkk):
            raise UserError(_('Tüm onay kutuları zorunludur.'))
        if not approver_name or not approver_email:
            raise UserError(_('Yetkili adı ve e-posta zorunludur.'))

        quote = offer.action_preview_quote(selected_ids=selected_ids, ad_budget=ad_budget)
        snapshot = {
            'offer': offer.get_public_payload(),
            'selected_ids': list(selected_ids),
            'ad_budget': ad_budget,
            'quote': {
                'net': float(pricing_svc.from_kurus(quote['net_kurus'])),
                'tax': float(pricing_svc.from_kurus(quote['tax_kurus'])),
                'gross': float(pricing_svc.from_kurus(quote['gross_kurus'])),
                'monthly_net': float(pricing_svc.from_kurus(quote['monthly']['net'])),
                'one_time_net': float(pricing_svc.from_kurus(quote['one_time']['net'])),
                'per_session_net': float(pricing_svc.from_kurus(quote['per_session']['net'])),
                'lines': quote['lines'],
            },
            'approver': {
                'name': approver_name,
                'email': approver_email,
                'company': approver_company or '',
                'phone': approver_phone or '',
            },
            'terms_version': offer.terms_version,
            'kvkk_version': offer.kvkk_version,
        }
        snap_str = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
        approval = Approval.create({
            'offer_id': offer.id,
            'approver_name': approver_name,
            'approver_company': approver_company or '',
            'approver_email': approver_email,
            'approver_phone': approver_phone or '',
            'selected_item_ids_json': json.dumps(list(selected_ids)),
            'ad_budget': ad_budget or 0,
            'net_total': float(pricing_svc.from_kurus(quote['net_kurus'])),
            'tax_total': float(pricing_svc.from_kurus(quote['tax_kurus'])),
            'gross_total': float(pricing_svc.from_kurus(quote['gross_kurus'])),
            'monthly_net': float(pricing_svc.from_kurus(quote['monthly']['net'])),
            'one_time_net': float(pricing_svc.from_kurus(quote['one_time']['net'])),
            'per_session_net': float(pricing_svc.from_kurus(quote['per_session']['net'])),
            'snapshot_json': snap_str,
            'snapshot_checksum': token_svc.snapshot_checksum(snap_str),
            'terms_version': offer.terms_version,
            'kvkk_version': offer.kvkk_version,
            'accepted_services': True,
            'accepted_terms': True,
            'accepted_kvkk': True,
            'approved_at': fields.Datetime.now(),
            'ip_masked': token_svc.mask_ip(ip),
            'user_agent': (user_agent or '')[:255],
            'idempotency_key': idempotency_key or token_svc.generate_session_token(),
        })
        offer.write({
            'status': 'approved',
            'approved_at': fields.Datetime.now(),
            'public_token_plaintext': False,
            'passcode_plaintext': False,
        })
        offer._log_event('approved', actor_type='public', summary=_('Teklif onaylandı'))
        line_names = [
            offer.item_ids.browse(i).name for i in selected_ids if offer.item_ids.browse(i).exists()
        ]
        offer._notify_admin(
            _('Teklif onaylandı: %s') % offer.offer_number,
            _(
                'Müşteri: %(partner)s<br/>Yetkili: %(name)s<br/>'
                'Seçilenler: %(items)s<br/>Genel toplam: %(total)s %(cur)s'
            ) % {
                'partner': offer.partner_id.display_name,
                'name': approver_name,
                'items': ', '.join(line_names),
                'total': approval.gross_total,
                'cur': offer.currency_id.name,
            },
        )
        return approval

    @api.model
    def _cron_expire_offers(self):
        today = fields.Date.context_today(self)
        offers = self.sudo().search([
            ('status', 'in', list(PUBLIC_OPEN_STATUSES)),
            ('valid_until', '<', today),
        ])
        for offer in offers:
            offer.write({'status': 'expired'})
            offer.session_ids.filtered(lambda s: not s.revoked).action_revoke()
            offer._log_event('expired', actor_type='system', summary=_('Süre doldu'))
        return True
