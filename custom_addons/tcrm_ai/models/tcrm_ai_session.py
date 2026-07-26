# Part of TCRM AI. See LICENSE for details.

import json
import logging
from datetime import datetime, timedelta

from tcrm import models, fields, api

_logger = logging.getLogger(__name__)

# Cap at 10 exchanges (20 messages) to reduce token usage and avoid quota limits
MAX_HISTORY_MESSAGES = 20


class TcrmAiSession(models.TransientModel):
    _name = 'tcrm.ai.session'
    _description = 'TCRM AI Chat Session (transient, per tab/channel)'

    session_id = fields.Char(required=True, index=True)
    history_json = fields.Text(default='[]')
    write_date = fields.Datetime(readonly=True)

    def get_history(self, session_id):
        """Return list of {role, content} for the session. Max 40 messages (last 20 exchanges)."""
        session = self.search([('session_id', '=', session_id)], limit=1)
        if not session:
            return []
        try:
            data = json.loads(session.history_json or '[]')
            if len(data) > MAX_HISTORY_MESSAGES:
                data = data[-MAX_HISTORY_MESSAGES:]
            return data
        except (TypeError, json.JSONDecodeError):
            return []

    # Alias for use when we have a recordset (single record)
    def _read_history_json(self):
        try:
            return json.loads(self.history_json or '[]')
        except (TypeError, json.JSONDecodeError):
            return []

    def append(self, session_id, role, content):
        """Append one message. role in ('user', 'assistant'). content is string."""
        session = self.search([('session_id', '=', session_id)], limit=1)
        history = session._read_history_json() if session else []
        history.append({'role': role, 'content': content or ''})
        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]
        payload = json.dumps(history)
        if session:
            session.write({'history_json': payload})
        else:
            self.create({'session_id': session_id, 'history_json': payload})

    def clear(self, session_id):
        """Clear conversation history for this session."""
        self.search([('session_id', '=', session_id)]).unlink()

    @api.model
    def _auto_vacuum_sessions(self):
        """Remove sessions older than 24h. Can be called from cron or on read."""
        expiry = datetime.now() - timedelta(hours=24)
        self.search([('write_date', '<', expiry.strftime('%Y-%m-%d %H:%M:%S'))]).unlink()
