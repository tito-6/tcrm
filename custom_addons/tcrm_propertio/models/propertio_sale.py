from tcrm import models, fields, api, _, SUPERUSER_ID
from tcrm.exceptions import UserError
from dateutil.relativedelta import relativedelta
import datetime

class PropertioSale(models.Model):
    _name = 'propertio.sale'
    _description = 'Property Sale Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tcrm.vector.sync.mixin', 'propertio.audit.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Sözleşme Referansı', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Müşteri', required=True, tracking=True)
    # Cross-module bridge: the CRM opportunity this sale originated from.
    opportunity_id = fields.Many2one('crm.lead', string='CRM Fırsatı', tracking=True, index=True,
                                     help='CRM opportunity this property sale originated from.')
    unit_id = fields.Many2one('propertio.unit', string='Birim', required=True, tracking=True, domain="[('state', '=', 'available')]")
    company_id = fields.Many2one('res.company', string='Şirket', related='unit_id.company_id', store=True, readonly=True, index=True)
    stage_id = fields.Many2one('propertio.sale.stage', string='Satış Aşaması')
    project_id = fields.Many2one('propertio.project', related='unit_id.project_id', string='Proje', store=True)
    block_id = fields.Many2one('propertio.block', related='unit_id.block_id', string='Blok', store=True)
    
    # Unit related fields for list view
    entrance = fields.Char(related='unit_id.entrance', string='Giriş', store=True)
    floor = fields.Char(related='unit_id.floor', string='Kat', store=True)
    gross_m2 = fields.Float(related='unit_id.gross_m2', string='Brüt m²', store=True)
    net_m2 = fields.Float(related='unit_id.net_m2', string='Net m²', store=True)
    general_gross_m2 = fields.Float(related='unit_id.general_gross_m2', string='Gen. Brüt m²', store=True)
    facade = fields.Char(related='unit_id.facade', string='Cephe', store=True)
    view_type = fields.Char(related='unit_id.view_type', string='Manzara', store=True)
    property_category_id = fields.Many2one('propertio.unit.category', related='unit_id.category_id', string='Gayrimenkul Kategorisi', store=True)
    status_id = fields.Many2one('propertio.unit.status', related='unit_id.status_id', string='Ana Durum', store=True)
    properties = fields.Properties('Contract Attributes', definition='stage_id.properties_definition')
    parking_no = fields.Char(related='unit_id.parking_no', string='Parking No', store=True)
    parking_type = fields.Selection(related='unit_id.parking_type', string='Parking Type', store=True)
    unit_code = fields.Char(related='unit_id.unit_code', string='Unit Code', store=True)
    tapu_ref = fields.Char(related='unit_id.tapu_ref', string='Tapu Ref', store=True)
    balcony_m2 = fields.Float(related='unit_id.balcony_m2', string='Balcony M2', store=True)
    terrace_m2 = fields.Float(related='unit_id.terrace_m2', string='Terrace M2', store=True)
    garden_m2 = fields.Float(related='unit_id.garden_m2', string='Garden M2', store=True)
    floor_gross_m2 = fields.Float(related='unit_id.floor_gross_m2', string='Floor Gross M2', store=True)
    ground_floor_m2 = fields.Float(related='unit_id.ground_floor_m2', string='Ground M2', store=True)
    normal_floor_m2 = fields.Float(related='unit_id.normal_floor_m2', string='Normal M2', store=True)
    
    sale_price = fields.Monetary(string='Satış Fiyatı', required=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    
    # Agency & Personnel
    agency_id = fields.Many2one('res.partner', string='Acente 1', domain=[('is_company', '=', True)])
    agency_2_id = fields.Many2one('res.partner', string='Acente 2', domain=[('is_company', '=', True)])
    sales_person_id = fields.Many2one('res.users', string='Satış Danışmanı 1', default=lambda self: self.env.user)
    sales_person_2_id = fields.Many2one('res.users', string='Satış Danışmanı 2')
    sales_office = fields.Char(string='Satış Ofisi')
    department_name = fields.Char(string='Departman')
    contact_person_id = fields.Many2one('res.users', string='İlgili Kişi')
    activity_person_id = fields.Many2one('res.users', string='Aktivite Sorumlusu')
    
    # Customer Details (Extended)
    customer_pid = fields.Char(string='TC Kimlik No')
    customer_passport = fields.Char(string='Pasaport No')
    father_name = fields.Char(string='Baba Adı')
    spouse_name = fields.Char(string='Eş Adı')
    accounting_code = fields.Char(string='Muhasebe Kodu')
    status_detail = fields.Char(string='Durum Detayı')
    is_vip = fields.Boolean(string='VIP Müşteri')
    vip_note = fields.Text(string='VIP Notu')
    
    # Contract Details
    contract_no = fields.Char(string='Manuel Sözleşme No')
    contract_date = fields.Date(string='Sözleşme Tarihi', default=fields.Date.context_today)
    notary_date = fields.Datetime(string='Noter Tarihi')
    notary_no = fields.Char(string='Noter Ref. No')
    is_notarized = fields.Boolean(string='Noter Onaylı mı?')
    notary_note = fields.Text(string='Noter Notu')
    
    # Financial Details
    payment_method_type = fields.Char(string='Ödeme Yöntemi Detayı') # e.g. "Cash + Installment"
    bank_approved = fields.Boolean(string='Banka Onaylı mı?')
    bank_approval_date = fields.Date(string='Banka Onay Tarihi')
    discount_amount = fields.Monetary(string='İndirim Tutarı', currency_field='currency_id')
    calc_discount_amount = fields.Monetary(string='Hesaplanan İndirim', currency_field='currency_id')
    maturity_diff = fields.Monetary(string='Vade Farkı', currency_field='currency_id')
    calc_maturity_diff = fields.Monetary(string='Hesaplanan Vade Farkı', currency_field='currency_id')
    invoice_status = fields.Selection([('to_invoice', 'Faturalanacak'), ('invoiced', 'Faturalandı')], string='Fatura Durumu')
    
    bank_doc_status = fields.Selection([
        ('none', 'Yok'),
        ('prepared', 'Hazırlandı'),
        ('submitted', 'Gönderildi'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi')
    ], string='Banka Belge Durumu', default='none')
    
    reserve_date = fields.Date(string='Rezervasyon Tarihi')
    credit_usage_date = fields.Date(string='Kredi Kullandırım Tarihi')
    
    feature_balcony_notes = fields.Char(string='Balkon Detayları (Ref: ES.KRK-01)')
    feature_window_notes = fields.Char(string='Pencere Detayları (Ref: ES.KRK-02)')
    
    # Exchange Rates Snapshot
    rate_tcmb = fields.Float(string='TCMB Kuru', digits=(12, 6))
    rate_down_payment = fields.Float(string='Peşinat Kuru', digits=(12, 6))
    rate_installment = fields.Float(string='Taksit Kuru', digits=(12, 6))
    
    group_customer_names = fields.Text(string='Grup Müşteri Adları')
    credit_term = fields.Integer(string='Kredi Vadesi (Ay)')
    is_project_active = fields.Boolean(string='Proje Aktif mi?', default=True)
    
    date_sale = fields.Date(string='Satış Tarihi', default=fields.Date.context_today, required=True)
    date_order = fields.Date(
        string='Order Date',
        related='date_sale',
        store=True,
        readonly=False,
        help='Compatibility alias used by legacy Propertio reports.',
    )
    
    installment_ids = fields.One2many('propertio.installment', 'sale_id', string='Payment Plan')
    document_ids = fields.One2many('propertio.document', 'sale_id', string='Documents')
    document_required_count = fields.Integer(compute='_compute_document_progress', string='Zorunlu')
    document_uploaded_count = fields.Integer(compute='_compute_document_progress', string='Yüklendi')
    
    total_paid = fields.Monetary(string='Toplam Ödenen', compute='_compute_totals', store=True)
    balance = fields.Monetary(string='Bakiye', compute='_compute_totals', store=True)
    total_amount = fields.Monetary(
        string='Total Amount',
        related='sale_price',
        store=True,
        readonly=False,
        currency_field='currency_id',
        help='Compatibility alias used by legacy Propertio reports.',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        related='sales_person_id',
        store=True,
        readonly=False,
        help='Compatibility alias used by legacy Propertio reports.',
    )

    state = fields.Selection([
        ('draft', 'Taslak'),
        ('confirmed', 'Onaylandı'),
        ('cancel', 'İptal Edildi'),
        ('refund', 'İade'),
    ], string='Durum', default='draft', tracking=True)
    state_reason = fields.Text(string='Durum Açıklaması', tracking=True)

    @api.depends('document_ids.is_required', 'document_ids.file')
    def _compute_document_progress(self):
        for r in self:
            req = r.document_ids.filtered(lambda d: d.is_required)
            r.document_required_count = len(req)
            r.document_uploaded_count = len(req.filtered(lambda d: d.file))

    @api.depends('installment_ids.amount', 'installment_ids.amount_paid')
    def _compute_totals(self):
        for record in self:
            paid = sum(inst.amount_paid for inst in record.installment_ids)
            total = sum(inst.amount for inst in record.installment_ids)
            record.total_paid = paid
            record.balance = record.sale_price - paid

    def _to_semantic_text(self):
        """Human-readable paragraph for vector RAG: customer, unit, price, payment status."""
        self.ensure_one()
        from datetime import date
        today = date.today()
        parts = []
        parts.append(f"Sale contract {self.name or 'N/A'}. Customer: {self.partner_id.name or 'N/A'}.")
        if self.unit_id:
            unit_desc = self.unit_code or self.unit_id.name or ''
            if self.project_id:
                unit_desc = f"{self.project_id.name} {self.block_id.name + ' ' if self.block_id else ''}{unit_desc}".strip()
            parts.append(f"Unit: {unit_desc}. Sale price: {self.sale_price} {self.currency_id.name if self.currency_id else ''}. State: {self.state}.")
        if self.stage_id:
            parts.append(f"Stage: {self.stage_id.name}.")
        parts.append(f"Total paid: {self.total_paid}. Balance: {self.balance}.")
        if self.installment_ids:
            overdue = self.installment_ids.filtered(lambda i: not i.is_paid and i.date_due and i.date_due < today)
            upcoming = self.installment_ids.filtered(lambda i: not i.is_paid and i.date_due and i.date_due >= today)
            if overdue:
                parts.append(f"Overdue installments: {len(overdue)}.")
            if upcoming:
                parts.append(f"Upcoming installments: {len(upcoming)}.")
        return " ".join(parts)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('propertio.sale') or 'New'
        return super(PropertioSale, self).create(vals_list)
    
    def action_rebalance_plan(self, context=None):
        """ Checks total vs price and creates a balancing installment or adjusts the last one """
        self.ensure_one()
        current_total = sum(self.installment_ids.mapped('amount'))
        diff = self.sale_price - current_total
        
        if abs(diff) > 0.01:
            last_date = fields.Date.context_today(self)
            if self.installment_ids:
                sorted_inst = self.installment_ids.sorted('date_due')
                last_date = sorted_inst[-1].date_due
            
            self.env['propertio.installment'].create({
                'sale_id': self.id,
                'name': 'Balance Adjustment',
                'date_due': last_date,
                'amount': diff,
                'type': 'balloon',
                'sequence': 999
            })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_confirm(self, context=None):
        for record in self:
            if record.state in ('cancel', 'refund'):
                raise UserError(_(
                    'İptal veya iade edilmiş sözleşme onaylanamaz. Önce taslağa alın.'
                ))
            record.state = 'confirmed'
            if record.unit_id:
                record.unit_id.state = 'sold'

    def action_cancel(self, context=None):
        """Cancel contract and free the unit (İptal Edildi)."""
        for record in self:
            if record.state == 'refund':
                raise UserError(_('İade edilmiş sözleşme iptal edilemez.'))
            if record.state == 'cancel':
                continue
            record.write({'state': 'cancel'})
            record._release_unit_if_safe()
            record.message_post(body=_('Satış sözleşmesi iptal edildi.'))
        return True

    def action_refund(self, context=None):
        """Mark contract as refunded (İade) and free the unit.

        Financial reversal of posted payments should still go through
        Ödeme İptal / Para İade workflow.
        """
        for record in self:
            if record.state == 'draft':
                raise UserError(_(
                    'Taslak sözleşme iade edilemez. Önce onaylayın veya iptal edin.'
                ))
            if record.state == 'refund':
                continue
            record.write({'state': 'refund'})
            record._release_unit_if_safe()
            record.message_post(body=_(
                'Satış sözleşmesi iade olarak işaretlendi. '
                'Ödenmiş tutarlar için Ödeme İptal / Para İade sürecini kullanın.'
            ))
        return True

    def action_reset_to_draft(self, context=None):
        for record in self:
            if record.state not in ('cancel', 'refund'):
                raise UserError(_('Yalnızca iptal veya iade kayıtları taslağa alınabilir.'))
            record.write({'state': 'draft'})
            if record.unit_id and record.unit_id.state == 'available':
                record.unit_id.state = 'option'
            record.message_post(body=_('Sözleşme tekrar taslağa alındı.'))
        return True

    def _release_unit_if_safe(self):
        """Set unit available when no other active sale holds it."""
        for record in self:
            unit = record.unit_id
            if not unit:
                continue
            other = self.search([
                ('unit_id', '=', unit.id),
                ('id', '!=', record.id),
                ('state', 'in', ('draft', 'confirmed')),
            ], limit=1)
            if other:
                continue
            open_offer = self.env['propertio.offer'].search([
                ('unit_id', '=', unit.id),
                ('state', 'in', ('draft', 'accepted')),
            ], limit=1)
            if open_offer and open_offer.state == 'draft':
                unit.state = 'option'
            else:
                unit.state = 'available'

    def action_view_installments(self, context=None):
        self.ensure_one()
        return {
            'name': 'Installments & Collections',
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.installment',
            'view_mode': 'list,graph,pivot,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id},
            'target': 'current',
        }

    def action_view_handover(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Handover',
            'res_model': 'propertio.handover',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id},
        }

    def action_view_title_deed(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Title Deed',
            'res_model': 'propertio.title.deed',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id},
        }

    def action_view_notary(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Notary',
            'res_model': 'propertio.notary',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id},
        }

    def action_view_unit(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.unit',
            'view_mode': 'form',
            'res_id': self.unit_id.id,
            'target': 'current',
        }

    def action_view_customer(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }

    def action_view_opportunity(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.opportunity_id.id,
            'target': 'current',
        }


    def action_view_payments(self, context=None):
        self.ensure_one()
        return {
            'name': 'Actual Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.payment',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id, 'default_partner_id': self.partner_id.id},
            'target': 'current',
        }

    def action_download_word(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/propertio/contract_word/{self.id}',
            'target': 'self',
        }

    def action_print_contract_html(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/html/tcrm_propertio.report_contract_document/{self.id}',
            'target': 'new',
        }

    def name_get(self):
        result = []
        for sale in self:
            name = f"#{sale.name} | {sale.partner_id.name} - {sale.unit_id.name}"
            result.append((sale.id, name))
        return result

    def action_export_batch_word(self, context=None):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/propertio/contract_word/batch?ids={",".join(map(str, self.ids))}',
            'target': 'self',
        }

    def action_download_pdf(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/propertio/contract_pdf/{self.id}',
            'target': 'self',
        }

    def action_open_full_screen(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.sale',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_whatsapp(self, context=None):
        self.ensure_one()
        template = self.env['propertio.whatsapp.template'].search([
            ('model', '=', 'propertio.sale'),
            ('active', '=', True),
        ], limit=1)
        url = template.get_whatsapp_url(self) if template else None
        if not url and self.partner_id:
            import urllib.parse
            phone = self.partner_id._propertio_whatsapp_phone_raw().replace(' ', '').replace('-', '').lstrip('+0')
            if len(phone) == 10:
                phone = '90' + phone
            url = 'https://wa.me/' + phone + '?text=' + urllib.parse.quote(
                _('Contract %s - Unit %s') % (self.name, self.unit_id.name or '')
            ) if phone else None
        return {'type': 'ir.actions.act_url', 'url': url or '#', 'target': 'new'}


class PropertioSaleStage(models.Model):
    _name = 'propertio.sale.stage'
    _description = 'Sale Stage'
    _order = 'sequence'
    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    properties_definition = fields.PropertiesDefinition('Contract Details View')


class PropertioInstallment(models.Model):
    _name = 'propertio.installment'
    _description = 'Payment Installment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'propertio.audit.mixin']
    _order = 'sequence, date_due'

    sale_id = fields.Many2one('propertio.sale', string='Sale Contract', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='sale_id.company_id', store=True, readonly=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    partner_id = fields.Many2one('res.partner', related='sale_id.partner_id', string='Customer', store=True)
    project_id = fields.Many2one('propertio.project', related='sale_id.project_id', string='Project', store=True)
    sales_person_id = fields.Many2one('res.users', related='sale_id.sales_person_id', string='Sales Person', store=True)
    name = fields.Char(string='Açıklama', required=True)  # örn. Peşinat, Taksit 1/12
    payment_method = fields.Char(string='Ödeme Yöntemi Detayı', related='sale_id.payment_method_type')
    
    date_due = fields.Date(string='Vade Tarihi', required=True)
    date_paid = fields.Date(string='Ödeme Tarihi', help='Taksitin tamamen ödendiği tarih.')
    amount = fields.Monetary(string='Tutar', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='sale_id.currency_id', readonly=True)
    
    amount_paid = fields.Monetary(string='Ödenen Tutar', currency_field='currency_id', tracking=True)
    residual = fields.Monetary(string='Kalan', compute='_compute_residual', store=True, currency_field='currency_id')
    is_paid = fields.Boolean(string='Ödendi', compute='_compute_residual', store=True, tracking=True)
    
    payment_status = fields.Selection([
        ('paid', 'Ödendi'),
        ('overdue', 'Gecikmiş'),
        ('upcoming', 'Yaklaşan'),
        ('future', 'İleri Tarihli')
    ], string='Ödeme Durumu', compute='_compute_payment_status', store=True)

    type = fields.Selection([
        ('down_payment', 'Peşinat'),
        ('installment', 'Taksit'),
        ('balloon', 'Balon Ödeme')
    ], string='Tip', default='installment')

    @api.depends('amount', 'amount_paid')
    def _compute_residual(self):
        for record in self:
            record.residual = record.amount - record.amount_paid
            if abs(record.residual) < 0.01: # Float tolerance
                record.residual = 0.0
                record.is_paid = True
            else:
                record.is_paid = False

    overdue_days = fields.Integer(
        string='Days Overdue',
        compute='_compute_overdue_days',
        store=True,
        help='Number of days past due date (0 if not overdue). Used for Red Alert report.'
    )

    @api.depends('is_paid', 'date_due')
    def _compute_payment_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.is_paid:
                record.payment_status = 'paid'
            elif record.date_due < today:
                record.payment_status = 'overdue'
            elif record.date_due <= today + relativedelta(days=30):
                record.payment_status = 'upcoming'
            else:
                record.payment_status = 'future'

    @api.depends('is_paid', 'date_due')
    def _compute_overdue_days(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.is_paid or not record.date_due:
                record.overdue_days = 0
            elif record.date_due < today:
                record.overdue_days = (today - record.date_due).days
            else:
                record.overdue_days = 0

    def write(self, vals):
        protected = {'amount', 'amount_paid', 'date_paid', 'date_due', 'sale_id', 'currency_id'}
        if (
            not self.env.context.get('propertio_financial_internal')
            and protected.intersection(vals)
            and self.env.uid != SUPERUSER_ID
        ):
            for rec in self:
                if rec.amount_paid or rec.is_paid:
                    rec._audit_log(
                        'blocked',
                        {'blocked_values': vals, 'message': 'Installment mutation requires refund/correction workflow.'},
                        sale_id=rec.sale_id.id,
                        original_model=rec._name,
                        original_res_id=rec.id,
                    )
                    rec.message_post(body=_('Blocked installment mutation. Use Cancellation/Refund (Para İade) through the related payment.'))
                    raise UserError(_('Paid installments are immutable. Use the payment Cancellation/Refund (Para İade) workflow.'))
        return super().write(vals)

    def unlink(self):
        if self.env.uid == SUPERUSER_ID or self.env.context.get('force_reallocate_delete'):
            return super().unlink()
        for rec in self:
            rec._audit_log(
                'blocked',
                {'message': 'Installment deletion blocked.'},
                sale_id=rec.sale_id.id,
                original_model=rec._name,
                original_res_id=rec.id,
            )
            rec.message_post(body=_('Deletion blocked by financial anti-fraud protocol. Archive/reverse the related payment instead.'))
        raise UserError(_('Installments cannot be deleted. Only the Software Owner can physically delete records.'))

    def action_open_reallocate_wizard(self):
        self.ensure_one()
        if self.amount_paid > 0:
            raise UserError(_("Kısmen veya tamamen ödenmiş bir taksit silinemez."))
            
        return {
            'name': _('Taksit Birleştir / Sil'),
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.installment.reallocate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_installment_id': self.id,
            }
        }

    def action_send_whatsapp(self, context=None):
        self.ensure_one()
        template = self.env['propertio.whatsapp.template'].search([
            ('model', '=', 'propertio.installment'),
            ('active', '=', True),
        ], limit=1)
        url = template.get_whatsapp_url(self) if template else None
        if not url and self.partner_id:
            import urllib.parse
            phone = self.partner_id._propertio_whatsapp_phone_raw().replace(' ', '').replace('-', '').lstrip('+0')
            if len(phone) == 10:
                phone = '90' + phone
            msg = _('Reminder: Installment %s - Amount %s due on %s') % (
                self.name, self.residual or self.amount, self.date_due or ''
            )
            url = 'https://wa.me/' + phone + '?text=' + urllib.parse.quote(msg) if phone else None
        return {'type': 'ir.actions.act_url', 'url': url or '#', 'target': 'new'}

    @api.model
    def action_open_danisman_karnesi_this_month(self, context=None):
        """Open Danışman Karnesi report filtered to paid installments this month."""
        from datetime import date
        today = date.today()
        first_day = (today.replace(day=1)).isoformat()
        today_str = today.isoformat()
        action = self.env['ir.actions.actions']._for_xml_id('tcrm_propertio.action_report_danisman_karnesi')
        action['domain'] = [
            ('is_paid', '=', True),
            ('date_paid', '>=', first_day),
            ('date_paid', '<=', today_str),
        ]
        action['name'] = _('Danışman Karnesi (Bu Ay Tahsilat)')
        return action



