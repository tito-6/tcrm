# Part of TCRM AI Research. See LICENSE for details.

from tcrm import api, fields, models
from tcrm.exceptions import AccessError, ValidationError


class TcrmAiDocument(models.Model):
    _name = 'tcrm.ai.document'
    _description = 'AI Research Document'
    _order = 'id desc'

    name = fields.Char(required=True)
    workspace_id = fields.Many2one(
        'tcrm.ai.workspace',
        required=True,
        ondelete='cascade',
        index=True,
    )
    attachment_id = fields.Many2one('ir.attachment', ondelete='cascade', index=True)
    company_id = fields.Many2one(
        related='workspace_id.company_id',
        store=True,
        index=True,
    )
    partner_id = fields.Many2one('res.partner', ondelete='set null', index=True)
    lead_id = fields.Many2one('crm.lead', ondelete='set null', index=True)
    res_model = fields.Char(index=True)
    res_id = fields.Integer(index=True)
    ragflow_document_id = fields.Char(index=True)
    ragflow_dataset_id = fields.Char(index=True)
    sync_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('ready', 'Ready'),
            ('failed', 'Failed'),
        ],
        default='draft',
        required=True,
        index=True,
    )
    sync_error = fields.Char()
    checksum = fields.Char(index=True)
    mime_type = fields.Char()
    file_size = fields.Integer()
    uploaded_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        required=True,
    )
    last_synced_at = fields.Datetime()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('workspace_id'):
                self.env['tcrm.ai.workspace'].browse(vals['workspace_id'])._check_membership()
            if vals.get('attachment_id'):
                att = self.env['ir.attachment'].browse(vals['attachment_id'])
                att.check_access('read')
                vals.setdefault('name', att.name)
                vals.setdefault('mime_type', att.mimetype)
                vals.setdefault('file_size', att.file_size)
        return super().create(vals_list)

    def unlink(self):
        from ..services.document_sync_service import DocumentSyncService
        service = DocumentSyncService(self.env)
        for rec in self:
            rec.workspace_id._check_membership()
            service.delete_remote(rec)
        return super().unlink()

    def action_sync(self):
        from ..services.document_sync_service import DocumentSyncService
        service = DocumentSyncService(self.env)
        for rec in self:
            service.sync_document(rec)
        return True

    def action_refresh_status(self):
        from ..services.document_sync_service import DocumentSyncService
        service = DocumentSyncService(self.env)
        for rec in self:
            service.refresh_status(rec)
        return True

    def action_retry_sync(self):
        self.write({'sync_state': 'pending', 'sync_error': False})
        return self.action_sync()

    @api.model
    def _cron_sync_pending(self):
        from ..services.document_sync_service import DocumentSyncService
        DocumentSyncService(self.env).cron_process_pending()
