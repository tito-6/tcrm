from tcrm import api, models, fields


class PropertioProject(models.Model):
    _name = 'propertio.project'
    _description = 'Real Estate Project'
    _order = 'name'

    name = fields.Char(string='Proje Adı', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    city = fields.Char(string='City', index=True)
    type_id = fields.Many2one('propertio.project.type', string='Project Type')
    stage_id = fields.Many2one('propertio.project.stage', string='Stage', group_expand='_read_group_stage_ids')
    properties = fields.Properties('Properties', definition='type_id.properties_definition')

    gdv = fields.Monetary(string='Gross Development Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    block_ids = fields.One2many('propertio.block', 'project_id', string='Bloklar')
    unit_ids = fields.One2many('propertio.unit', 'project_id', string='Units')
    unit_count = fields.Integer(string='Total Units', compute='_compute_unit_count')

    standard_feature_ids = fields.Many2many(
        'propertio.feature', 'project_standard_feature_rel',
        'project_id', 'feature_id', string='Standart Olanaklar')
    extra_feature_ids = fields.Many2many(
        'propertio.feature', 'project_extra_feature_rel',
        'project_id', 'feature_id', string='Mevcut Yükseltmeler')

    def _compute_unit_count(self):
        for record in self:
            record.unit_count = self.env['propertio.unit'].search_count([('project_id', '=', record.id)])

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Always show all company stages in kanban, including empty columns."""
        Stage = self.env['propertio.project.stage']
        return Stage.search([
            '|', ('company_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
            ('active', '=', True),
        ], order='sequence, id')


class PropertioProjectType(models.Model):
    _name = 'propertio.project.type'
    _description = 'Project Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string='Code', index=True, help='Stable technical code for idempotent seeding.')
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)
    properties_definition = fields.PropertiesDefinition('Unit Properties')


class PropertioProjectStage(models.Model):
    _name = 'propertio.project.stage'
    _description = 'Project Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string='Code', index=True, help='Stable technical code for idempotent seeding.')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='Projects in this stage are folded by default in the kanban view.')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(default=True)


class PropertioBlock(models.Model):
    _name = 'propertio.block'
    _description = 'Project Block'
    _order = 'name'

    name = fields.Char(string='Block Name', required=True)
    project_id = fields.Many2one('propertio.project', string='Project', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='project_id.company_id', store=True, readonly=True, index=True)
    unit_ids = fields.One2many('propertio.unit', 'block_id', string='Units')
