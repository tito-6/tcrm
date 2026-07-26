# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import api, models
from ..websocket import WebsocketConnectionHandler


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        session_info["websocket_worker_version"] = WebsocketConnectionHandler._VERSION
        return session_info

    def session_info(self):
        session_info = super().session_info()
        session_info["websocket_worker_version"] = WebsocketConnectionHandler._VERSION
        return session_info
