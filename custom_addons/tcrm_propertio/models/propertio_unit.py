from tcrm import models, fields, api

class PropertioUnit(models.Model):
    _name = 'propertio.unit'
    _description = 'Real Estate Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tcrm.vector.sync.mixin', 'propertio.audit.mixin']
    _order = 'project_id, block_id, unit_number'
    # Use name_search or display_name to show Project - Block - Unit

    name = fields.Char(string='Birim No', required=True, index=True)
    unit_number = fields.Char(string='Birim Numarası', related='name', store=True) # visual alias
    
    project_id = fields.Many2one('propertio.project', string='Proje', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Şirket', related='project_id.company_id', store=True, readonly=True, index=True)
    block_id = fields.Many2one('propertio.block', string='Blok', domain="[('project_id', '=', project_id)]", index=True)
    
    floor = fields.Char(string='Kat')
    entrance = fields.Char(string='Giriş')
    view_type = fields.Char(string='Manzara') # e.g. "Sea View", "Garden"
    
    gross_m2 = fields.Float(string='Brüt m²', digits=(10, 2))
    net_m2 = fields.Float(string='Net m²', digits=(10, 2))
    general_gross_m2 = fields.Float(string='Genel Brüt m²', digits=(10, 2), help="Ortak alanlar dahil")
    balcony_m2 = fields.Float(string='Balkon m²', digits=(10, 2))
    terrace_m2 = fields.Float(string='Teras m²', digits=(10, 2))
    garden_m2 = fields.Float(string='Bahçe m²', digits=(10, 2))
    floor_gross_m2 = fields.Float(string='Kat Brüt m²', digits=(10, 2))
    ground_floor_m2 = fields.Float(string='Zemin Kat m²', digits=(10, 2))
    normal_floor_m2 = fields.Float(string='Normal Kat m²', digits=(10, 2))
    
    facade = fields.Char(string='Cephe', help="Kuzey, Güney vb.")
    parking_no = fields.Char(string='Otopark No')
    parking_type = fields.Selection([('open', 'Açık'), ('closed', 'Kapalı')], string='Otopark Tipi')
    
    unit_code = fields.Char(string='Birim Kodu')
    tapu_ref = fields.Char(string='Tapu Ref.')
    accounting_code = fields.Char(string='Muhasebe Kodu')
    category_id = fields.Many2one('propertio.unit.category', string='Gayrimenkul Kategorisi')
    status_id = fields.Many2one('propertio.unit.status', string='Özel Durum')
    properties = fields.Properties('Özel Özellikler', definition='category_id.properties_definition')
    
    state = fields.Selection([
        ('available', 'Müsait'),
        ('option', 'Opsiyon'),
        ('sold', 'Satıldı'),
        ('handover', 'Teslim')
    ], string='Durum', default='available', required=True, index=True, tracking=True)
    
    list_price = fields.Monetary(string='Liste Fiyatı', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Para Birimi', related='project_id.currency_id', readonly=True)
    
    standard_feature_ids = fields.Many2many('propertio.feature', 'unit_standard_feature_rel',
                                            'unit_id', 'feature_id', string='Standart Olanaklar')
    extra_feature_ids = fields.Many2many('propertio.feature', 'unit_extra_feature_rel',
                                        'unit_id', 'feature_id', string='Eklenebilir Özellikler')
    
    # Digital Assets / Media
    # In the view, use <field name="attachment_ids" widget="many2many_binary"/> or standard attachment box
    # If a specific relationship is needed for the "Digital Assets" tab logic:
    attachment_ids = fields.Many2many('ir.attachment', string='Digital Assets', help='Attach Catalogs, Factsheets, Renders here.')

    # Reporting Fields
    sale_ids = fields.One2many('propertio.sale', 'unit_id', string='Sales History')
    current_sale_id = fields.Many2one('propertio.sale', compute='_compute_sale_metrics', store=True)
    
    sold_value = fields.Monetary(string='Sold Value', compute='_compute_sale_metrics', store=True, currency_field='currency_id')
    collected_amount = fields.Monetary(string='Collected', compute='_compute_sale_metrics', store=True, currency_field='currency_id')
    receivable_amount = fields.Monetary(string='Receivable', compute='_compute_sale_metrics', store=True, currency_field='currency_id')
    offer_count = fields.Integer(string='Offers', compute='_compute_offer_count')

    @api.depends('sale_ids.state', 'sale_ids.sale_price', 'sale_ids.total_paid')
    def _compute_sale_metrics(self):
        for unit in self:
            # Find active sale (confirmed or draft if no confirmed? standard is confirmed)
            # Logic: Last confirmed sale, or last draft if none.
            # Ideally state='sold' implies confirmed sale.
            active_sale = unit.sale_ids.filtered(lambda s: s.state == 'confirmed')
            # Take the latest one
            sale = active_sale[:1]
            
            unit.current_sale_id = sale.id
            if sale:
                unit.sold_value = sale.sale_price
                unit.collected_amount = sale.total_paid
                unit.receivable_amount = sale.balance
            else:
                unit.sold_value = 0.0
                unit.collected_amount = 0.0
                unit.receivable_amount = 0.0

    def _to_semantic_text(self):
        """Human-readable paragraph for vector RAG: project, unit, specs, price, state."""
        self.ensure_one()
        parts = []
        if self.project_id:
            parts.append(f"Project: {self.project_id.name}.")
        if self.block_id:
            parts.append(f"Block: {self.block_id.name}.")
        parts.append(f"Unit: {self.name or ''}. Unit code: {self.unit_code or 'N/A'}.")
        if self.floor:
            parts.append(f"Floor: {self.floor}.")
        if self.entrance:
            parts.append(f"Entrance: {self.entrance}.")
        if self.view_type:
            parts.append(f"View: {self.view_type}.")
        if self.gross_m2:
            parts.append(f"Gross m²: {self.gross_m2}.")
        if self.net_m2:
            parts.append(f"Net m²: {self.net_m2}.")
        if self.list_price:
            parts.append(f"List price: {self.list_price} {self.currency_id.name if self.currency_id else ''}.")
        parts.append(f"Status: {self.state}.")
        if self.category_id:
            parts.append(f"Category: {self.category_id.name}.")
        if self.status_id:
            parts.append(f"Custom status: {self.status_id.name}.")
        return " ".join(parts)

    def name_get(self):
        result = []
        for unit in self:
            name = f"{unit.project_id.name} - {unit.block_id.name} - {unit.name}" if unit.block_id else f"{unit.project_id.name} - {unit.name}"
            result.append((unit.id, name))
        return result

    @api.depends()
    def _compute_offer_count(self):
        for unit in self:
            unit.offer_count = self.env['propertio.offer'].search_count([('unit_id', '=', unit.id), ('state', '=', 'draft')])

    def action_view_sales_history(self, context=None):
        self.ensure_one()
        return {
            'name': 'Sales History',
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.sale',
            'view_mode': 'list,form',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
            'target': 'current',
        }

    def action_view_offers(self, context=None):
        self.ensure_one()
        return {
            'name': 'Offers',
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.offer',
            'view_mode': 'list,form',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
            'target': 'current',
        }

    def action_generate_qr(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/propertio/unit/qr/%s' % self.id,
            'target': 'new',
        }

class PropertioFeature(models.Model):
    _name = 'propertio.feature'
    _description = 'Unit Feature'

    name = fields.Char(string='Feature', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    color = fields.Integer(string='Color')
    icon = fields.Char(string='Icon Class', help="FontAwesome class, e.g. fa-swimming-pool")

class PropertioUnitCategory(models.Model):
    _name = 'propertio.unit.category'
    _description = 'Unit Category'
    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)
    properties_definition = fields.PropertiesDefinition('Extra Attributes')

class PropertioUnitStatus(models.Model):
    _name = 'propertio.unit.status'
    _description = 'Unit Detailed Status'
    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)
