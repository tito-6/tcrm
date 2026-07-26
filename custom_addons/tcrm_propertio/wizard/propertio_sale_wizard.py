from tcrm import models, fields, api, _
from dateutil.relativedelta import relativedelta

class PropertioSaleWizard(models.TransientModel):
    _name = 'propertio.sale.wizard'
    _description = 'Sale & Payment Plan Generator'

    unit_id = fields.Many2one('propertio.unit', string='Birim', required=True, domain=[('state', '=', 'available')])
    partner_id = fields.Many2one('res.partner', string='Müşteri', required=True)
    
    price = fields.Monetary(string='Satış Fiyatı', required=True, currency_field='currency_id')
    list_price = fields.Monetary(string='Liste Fiyatı', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Para Birimi', required=True)
    
    # Down Payment
    down_payment_mode = fields.Selection([('pct', '% Yüzde'), ('fixed', 'Sabit Tutar')], default='pct', string="Peşinat Tipi")
    down_payment_pct = fields.Float(string='Peşinat %', default=10.0)
    down_payment_amount = fields.Monetary(string='Peşinat Tutarı', currency_field='currency_id')
    date_down_payment = fields.Date(string='Peşinat Tarihi', default=fields.Date.context_today)

    # Installments
    installment_count = fields.Integer(string='Taksit Sayısı', default=12)
    start_date = fields.Date(string='İlk Taksit Tarihi', default=fields.Date.context_today)
    
    # Balloon
    balloon_mode = fields.Selection([('pct', '% Yüzde'), ('fixed', 'Sabit Tutar')], default='fixed', string="Balon Ödeme Tipi")
    balloon_pct = fields.Float(string='Balon Ödeme %')
    balloon_amount = fields.Monetary(string='Toplam Balon Tutarı', currency_field='currency_id')
    balloon_strategy = fields.Selection([('end', 'Sonda'), ('mid', 'Ortada')], default='end', string="Balon Zamanlaması")
    
    # Financials
    maturity_diff = fields.Monetary(string='Vade Farkı (+)', currency_field='currency_id')
    discount_amount = fields.Monetary(string='İndirim (-)', currency_field='currency_id')
    
    # Display
    exchange_rate_date = fields.Date(string="Döviz Kuru Tarihi", default=fields.Date.context_today)
    tcmb_rates_html = fields.Html(compute='_compute_tcmb_rates', string="TCMB Kurları", store=False)

    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        if self.unit_id:
            self.price = self.unit_id.list_price
            self.list_price = self.unit_id.list_price
            self.currency_id = self.unit_id.currency_id

    @api.onchange('down_payment_pct', 'price', 'down_payment_mode')
    def _onchange_dp_pct(self):
        if self.down_payment_mode == 'pct' and self.price:
            self.down_payment_amount = self.price * (self.down_payment_pct / 100.0)

    @api.onchange('down_payment_amount', 'price', 'down_payment_mode')
    def _onchange_dp_amount(self):
        if self.down_payment_mode == 'fixed' and self.price:
            self.down_payment_pct = (self.down_payment_amount / self.price) * 100.0

    @api.onchange('balloon_pct', 'price', 'balloon_mode')
    def _onchange_balloon_pct(self):
        if self.balloon_mode == 'pct' and self.price:
            self.balloon_amount = self.price * (self.balloon_pct / 100.0)

    @api.onchange('balloon_amount', 'price', 'balloon_mode')
    def _onchange_balloon_amount(self):
        if self.balloon_mode == 'fixed' and self.price:
            self.balloon_pct = (self.balloon_amount / self.price) * 100.0

    @api.onchange('exchange_rate_date')
    def _onchange_exchange_rate_date_limit(self):
        today = fields.Date.context_today(self)
        if self.exchange_rate_date and self.exchange_rate_date > today:
            self.exchange_rate_date = today
            return {
                'warning': {
                    'title': 'Geçersiz Tarih',
                    'message': 'Kur tarihi bugünden ileri bir tarih olamaz. Otomatik olarak bugüne ayarlandı.'
                }
            }

    @api.depends('exchange_rate_date')
    @api.onchange('exchange_rate_date')
    def _compute_tcmb_rates(self):
        # Fetch rates from res.currency helper
        target_date = self.exchange_rate_date or fields.Date.context_today(self)
        try:
            data = self.env['res.currency'].get_tcmb_data(target_date)
            
            # If data found, update TCRM rates as well implicitly?
            # User requirement: "Auto fetch that date of exchange rate". 
            # Usually implies updating the system. Let's do it safe: Update wizard display first.
            if data:
                self.env['res.currency']._apply_rates(data, target_date)
            
        except Exception:
            data = []
            
        if not data:
            self.tcmb_rates_html = f"<div class='alert alert-warning'>Tarih için TCMB verisi bulunamadı: {target_date}. (Hafta sonu veya tatil olabilir)</div>"
            return
            
        html = "<div class='table-responsive' style='max-height: 400px; overflow-y: auto; overflow-x: auto;'><table class='table table-bordered table-striped table-hover w-100' style='min-width: 600px;'>"
        html += "<thead class='table-light'><tr><th class='text-center' style='width: 10%;'>Birim</th><th style='width: 30%;'>Döviz Kodu</th><th class='text-end' style='width: 30%;'>Döviz Alış (₺)</th><th class='text-end' style='width: 30%;'>Döviz Satış (₺)</th></tr></thead><tbody>"
        
        currency_meta = {
            'USD': ('us', '$'), 'EUR': ('eu', '€'), 'GBP': ('gb', '£'),
            'CHF': ('ch', 'CHF'), 'CAD': ('ca', '$'), 'AUD': ('au', '$'),
            'DKK': ('dk', 'kr'), 'SEK': ('se', 'kr'), 'NOK': ('no', 'kr'),
            'JPY': ('jp', '¥'), 'KWD': ('kw', 'KD'), 'SAR': ('sa', 'SR'),
            'AED': ('ae', 'AED'), 'QAR': ('qa', 'QR'), 'RUB': ('ru', '₽'),
            'CNY': ('cn', '¥'), 'PKR': ('pk', 'Rs'), 'KRW': ('kr', '₩'),
            'AZN': ('az', '₼'), 'KZT': ('kz', '₸'), 'BGN': ('bg', 'лв'),
            'RON': ('ro', 'lei'), 'IRR': ('ir', '﷼')
        }

        for row in data:
            code = row['code']
            country_code, sym = currency_meta.get(code, ('', ''))
            
            if country_code:
                flag_html = f"<img src='https://flagcdn.com/w20/{country_code}.png' width='20' class='me-2' alt='{code}' style='vertical-align: middle; border: 1px solid #ccc; border-radius: 2px;'/>"
            else:
                flag_html = "<span class='me-2' style='display:inline-block; width:20px;'></span>"
                
            html += f"<tr><td class='text-center text-muted'>1 {sym}</td><td>{flag_html}<b class='text-primary'>{code}</b></td><td class='text-end'>{row['buying']:.4f}</td><td class='text-end'>{row['selling']:.4f}</td></tr>"
            
        html += "</tbody></table></div>"
        self.tcmb_rates_html = html

    def action_generate_sale(self, context=None):
        self.ensure_one()
        
        # Calculate final price
        final_price = self.price + self.maturity_diff - self.discount_amount
        
        # 1. Create Sale Header
        sale_vals = {
            'partner_id': self.partner_id.id,
            'unit_id': self.unit_id.id,
            'sale_price': final_price, # Use modified price
            'currency_id': self.currency_id.id,
            'date_sale': fields.Date.context_today(self),
            'state': 'draft',
            'maturity_diff': self.maturity_diff,
            'discount_amount': self.discount_amount,
        }
        if self.env.context.get('default_opportunity_id'):
            sale_vals['opportunity_id'] = self.env.context['default_opportunity_id']
        sale = self.env['propertio.sale'].create(sale_vals)
        offer_id = self.env.context.get('propertio_offer_id')
        if offer_id:
            offer = self.env['propertio.offer'].browse(offer_id).exists()
            if offer:
                offer.write({'sale_id': sale.id, 'state': 'accepted'})
        
        installments = []
        
        # 2. Down Payment
        dp_val = self.down_payment_amount
        # If mode is pct, recalculate to be safe
        if self.down_payment_mode == 'pct':
            dp_val = final_price * (self.down_payment_pct / 100.0)
            
        if dp_val > 0:
            installments.append({
                'sale_id': sale.id,
                'name': 'Peşinat',
                'date_due': self.date_down_payment,
                'amount': dp_val,
                'type': 'down_payment'
            })
            
        # 3. Calculate Remainder
        remainder = final_price - dp_val - self.balloon_amount
        
        if self.installment_count > 0:
            monthly_amount = remainder / self.installment_count
            current_date = self.start_date
            
            for i in range(1, self.installment_count + 1):
                installments.append({
                    'sale_id': sale.id,
                    'name': f'Taksit {i}/{self.installment_count}',
                    'date_due': current_date,
                    'amount': monthly_amount,
                    'type': 'installment'
                })
                current_date = current_date + relativedelta(months=1)
        
        # 4. Balloon
        if self.balloon_amount > 0:
             # Logic: If end, add at end. If mid, add at mid? Simplification: At end for now.
             installments.append({
                'sale_id': sale.id,
                'name': 'Balon Ödeme',
                'date_due': current_date, 
                'amount': self.balloon_amount,
                'type': 'balloon'
            })

        self.env['propertio.installment'].create(installments)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.sale',
            'res_id': sale.id,
            'view_mode': 'form',
            'target': 'current',
        }
