# Part of TCRM AI Research. See LICENSE for details.
"""Synchronize Odoo AI documents with RAGFlow datasets."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from tcrm.exceptions import AccessError, UserError, ValidationError

from .config import get_ragflow_config
from .exceptions import RagflowError, RagflowNotFoundError
from . import ragflow_client as ragflow_client_mod

_logger = logging.getLogger(__name__)


class DocumentSyncService:
    """Upload / parse / status-check documents for a workspace."""

    def __init__(self, env, correlation_id: str | None = None):
        self.env = env
        self.correlation_id = correlation_id or str(uuid.uuid4())

    def compute_checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def validate_upload(self, filename: str, content: bytes) -> None:
        cfg = get_ragflow_config(self.env)
        if not content:
            raise ValidationError(self.env._('Empty file is not allowed.'))
        if len(content) > cfg['max_upload_size_bytes']:
            raise ValidationError(
                self.env._('File exceeds maximum upload size of %s MB.')
                % cfg['max_upload_size_mb']
            )
        ext = ''
        if '.' in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
        if ext and ext not in cfg['allowed_extensions']:
            raise ValidationError(
                self.env._('File type ".%s" is not allowed.') % ext
            )

    def sync_document(self, document) -> Any:
        """
        Upload (if needed) and trigger parsing for an ai.document record.

        Uses the current user ACL on the document; narrow sudo is not used.
        """
        document.ensure_one()
        document.check_access('write')
        workspace = document.workspace_id
        if not workspace._user_is_member():
            raise AccessError(self.env._('You are not a member of this workspace.'))

        dataset_id = workspace.ragflow_dataset_id or get_ragflow_config(self.env)['default_dataset_id']
        if not dataset_id:
            raise UserError(self.env._('No RAGFlow dataset configured for this workspace.'))

        attachment = document.attachment_id
        if not attachment:
            raise UserError(self.env._('Document has no attachment.'))
        attachment.check_access('read')
        content = attachment.raw or b''
        if not content and attachment.datas:
            # datas is base64; prefer raw when available (Odoo 19).
            content = attachment.raw
        if not content:
            raise UserError(self.env._('Attachment content is empty.'))

        checksum = self.compute_checksum(content)
        document.write({
            'checksum': checksum,
            'mime_type': attachment.mimetype,
            'file_size': len(content),
            'sync_state': 'pending',
            'sync_error': False,
            'ragflow_dataset_id': dataset_id,
        })

        provider = ragflow_client_mod.get_research_provider(self.env, correlation_id=self.correlation_id)
        try:
            # Re-upload when checksum changed or no external id.
            if (
                not document.ragflow_document_id
                or document.checksum != checksum
            ):
                if document.ragflow_document_id and document.checksum != checksum:
                    try:
                        provider.delete_document(dataset_id, [document.ragflow_document_id])
                    except RagflowError:
                        _logger.info(
                            'ragflow_resync_delete_skip correlation_id=%s document_id=%s',
                            self.correlation_id,
                            document.id,
                        )
                uploaded = provider.upload_document(
                    dataset_id,
                    document.name or attachment.name or 'document',
                    content,
                    content_type=attachment.mimetype,
                )
                document.write({
                    'ragflow_document_id': uploaded['id'],
                    'sync_state': 'processing',
                })
            else:
                document.write({'sync_state': 'processing'})

            provider.parse_documents(dataset_id, [document.ragflow_document_id])
            document.write({'sync_state': 'processing', 'sync_error': False})
            _logger.info(
                'ragflow_doc_sync correlation_id=%s document_id=%s workspace_id=%s state=processing',
                self.correlation_id,
                document.id,
                workspace.id,
            )
        except RagflowError as exc:
            document.write({
                'sync_state': 'failed',
                'sync_error': str(exc)[:500],
            })
            _logger.warning(
                'ragflow_doc_sync_failed correlation_id=%s document_id=%s category=%s',
                self.correlation_id,
                document.id,
                exc.category,
            )
            raise UserError(self.env._('Document synchronization failed. Please retry later.')) from exc
        return document

    def refresh_status(self, document) -> Any:
        document.ensure_one()
        document.check_access('read')
        if not document.ragflow_document_id or not document.ragflow_dataset_id:
            return document
        provider = ragflow_client_mod.get_research_provider(self.env, correlation_id=self.correlation_id)
        try:
            status = provider.get_document_status(
                document.ragflow_dataset_id,
                document.ragflow_document_id,
            )
        except RagflowNotFoundError:
            document.write({
                'sync_state': 'failed',
                'sync_error': self.env._('Document missing in RAGFlow; re-sync required.'),
            })
            return document
        except RagflowError as exc:
            document.write({'sync_error': str(exc)[:500]})
            return document

        run = (status.get('run') or '').upper()
        vals: dict[str, Any] = {'sync_error': False}
        if run in ('DONE', 'SUCCESS'):
            vals['sync_state'] = 'ready'
            from tcrm.fields import Datetime
            vals['last_synced_at'] = Datetime.now()
        elif run in ('FAIL', 'FAILED', 'CANCEL', 'CANCELLED'):
            vals['sync_state'] = 'failed'
            vals['sync_error'] = self.env._('RAGFlow processing failed (%s).') % run
        else:
            vals['sync_state'] = 'processing'
        document.write(vals)
        return document

    def delete_remote(self, document) -> None:
        """Best-effort delete of the RAGFlow document mapping."""
        if not document.ragflow_document_id or not document.ragflow_dataset_id:
            return
        try:
            provider = ragflow_client_mod.get_research_provider(self.env, correlation_id=self.correlation_id)
            provider.delete_document(
                document.ragflow_dataset_id,
                [document.ragflow_document_id],
            )
        except RagflowError as exc:
            _logger.warning(
                'ragflow_doc_delete_failed correlation_id=%s document_id=%s category=%s',
                self.correlation_id,
                document.id,
                exc.category,
            )

    def cron_process_pending(self) -> None:
        Document = self.env['tcrm.ai.document']
        pending = Document.search([
            ('sync_state', 'in', ('pending', 'processing')),
        ], limit=50)
        for doc in pending:
            try:
                if doc.sync_state == 'pending':
                    self.sync_document(doc)
                else:
                    self.refresh_status(doc)
            except Exception:
                _logger.exception(
                    'ragflow_cron_doc_error correlation_id=%s document_id=%s',
                    self.correlation_id,
                    doc.id,
                )
