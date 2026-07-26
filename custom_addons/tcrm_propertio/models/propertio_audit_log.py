# -*- coding: utf-8 -*-
import json

from tcrm import api, fields, models


class PropertioAuditLog(models.Model):
    _name = 'propertio.audit.log'
    _description = 'Propertio audit trail (deletes and field changes)'
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    model_name = fields.Char(required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda s: s.env.company, index=True)
    res_id = fields.Integer(required=True, index=True)
    record_name = fields.Char(string='Record')
    action_type = fields.Selection(
        [
            ('unlink', 'Deleted'),
            ('write', 'Updated'),
            ('reverse', 'Reversed'),
            ('blocked', 'Blocked'),
            ('approval', 'Approval'),
        ],
        string='Action',
        required=True,
        index=True,
    )
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda s: s.env.user.id)
    details = fields.Text(string='Details')
    sale_id = fields.Many2one('propertio.sale', string='Sale Contract', index=True)
    original_model = fields.Char(index=True)
    original_res_id = fields.Integer(index=True)
    reversal_model = fields.Char(index=True)
    reversal_res_id = fields.Integer(index=True)
    reason_code = fields.Char(index=True)
    explanation = fields.Text()
    requires_manager_approval = fields.Boolean(default=False)
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    approved_date = fields.Datetime(string='Approved On')

    @api.depends('model_name', 'res_id', 'action_type')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s #%s — %s' % (rec.model_name, rec.res_id, rec.action_type or '')


class PropertioAuditMixin(models.AbstractModel):
    _name = 'propertio.audit.mixin'
    _description = 'Store audit entries on unlink and on write (changed fields only)'

    def _audit_snapshot(self):
        self.ensure_one()
        out = {}
        for name, field in self._fields.items():
            ftype = getattr(field, 'type', None)
            if ftype in ('one2many', 'many2many', 'binary', 'properties', 'properties_definition'):
                continue
            if field.compute and not field.store:
                continue
            try:
                out[name] = self[name]
            except Exception:
                continue
        return out

    def _audit_log(self, action_type, details=None, **extra):
        for rec in self:
            values = {
                'model_name': rec._name,
                'company_id': getattr(rec, 'company_id', self.env.company).id or self.env.company.id,
                'res_id': rec.id,
                'record_name': rec.display_name,
                'action_type': action_type,
                'user_id': self.env.user.id,
                'details': json.dumps(details or {}, default=str),
            }
            values.update({k: v for k, v in extra.items() if v not in (None, False)})
            self.env['propertio.audit.log'].sudo().create(values)

    def write(self, vals):
        if self.env.context.get('propertio_audit_skip'):
            return super().write(vals)
        keys = [k for k in vals if k in self._fields and not k.startswith('message_')]
        if not keys:
            return super().write(vals)
        before = {rec.id: {k: rec[k] for k in keys if k in rec._fields} for rec in self}
        res = super().write(vals)
        Log = self.env['propertio.audit.log'].sudo()
        for rec in self:
            old = before.get(rec.id, {})
            changes = {}
            for k in old:
                try:
                    if old[k] != rec[k]:
                        changes[k] = {'old': old[k], 'new': rec[k]}
                except Exception:
                    continue
            if changes:
                Log.create({
                    'model_name': rec._name,
                    'company_id': rec.env.company.id,
                    'res_id': rec.id,
                    'record_name': rec.display_name,
                    'action_type': 'write',
                    'user_id': self.env.user.id,
                    'details': json.dumps(changes, default=str),
                })
        return res

    def unlink(self):
        if self.env.context.get('propertio_audit_skip'):
            return super().unlink()
        Log = self.env['propertio.audit.log'].sudo()
        for rec in self:
            snap = rec._audit_snapshot()
            Log.create({
                'model_name': rec._name,
                'company_id': rec.env.company.id,
                'res_id': rec.id,
                'record_name': rec.display_name,
                'action_type': 'unlink',
                'user_id': self.env.user.id,
                'details': json.dumps(snap, default=str),
            })
        return super().unlink()
