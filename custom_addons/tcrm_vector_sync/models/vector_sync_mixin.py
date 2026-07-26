# Part of TCRM Vector Sync. See LICENSE for details.

"""Abstract mixin: enqueue create/write/unlink to vector sync queue for remote RAG ingest."""

import logging

from tcrm import api, models

_logger = logging.getLogger(__name__)


class VectorSyncMixin(models.AbstractModel):
    _name = 'tcrm.vector.sync.mixin'
    _description = 'TCRM Vector Sync Mixin'
    _abstract = True

    def _to_semantic_text(self):
        """
        Override in subclasses to return human-readable paragraph(s) for this record.
        Used as the text payload for vector embedding.
        """
        return ''

    def _vector_sync_enqueue(self, action, text=None):
        """Enqueue one record for sync in a separate DB transaction so failures do not abort the main request."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('tcrm.ai_base_url', '').strip()
        if not base_url:
            _logger.debug("tcrm.ai_base_url not set; skipping vector enqueue for %s %s", self._name, self.ids)
            return
        # Use a separate cursor/transaction so any failure here does not abort the main request (e.g. Discuss chat).
        try:
            with self.env.registry.cursor() as new_cr:
                new_env = api.Environment(new_cr, api.SUPERUSER_ID, {})
                Queue = new_env['tcrm.vector.sync.queue']
                for record in self:
                    Queue.create({
                        'model': record._name,
                        'record_id': record.id,
                        'text': text or '',
                        'action': action,
                    })
                new_cr.commit()
        except Exception as e:
            _logger.warning("Vector sync enqueue failed for %s %s: %s", self._name, self.ids, e)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            try:
                text = rec._to_semantic_text()
                rec._vector_sync_enqueue('upsert', text=text)
            except Exception as e:
                _logger.warning("Vector sync enqueue after create %s %s: %s", rec._name, rec.id, e)
        return records

    def write(self, vals):
        result = super().write(vals)
        for rec in self:
            try:
                text = rec._to_semantic_text()
                rec._vector_sync_enqueue('upsert', text=text)
            except Exception as e:
                _logger.warning("Vector sync enqueue after write %s %s: %s", rec._name, rec.id, e)
        return result

    def unlink(self):
        for rec in self:
            try:
                rec._vector_sync_enqueue('delete')
            except Exception as e:
                _logger.warning("Vector sync enqueue before unlink %s %s: %s", rec._name, rec.id, e)
        return super().unlink()
