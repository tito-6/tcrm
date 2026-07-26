import re

from tcrm import http
from tcrm.http import request


class TcrmCommandPaletteController(http.Controller):
    @http.route("/tcrm_master/command_palette", type="jsonrpc", auth="user")
    def command_palette(self, query=None):
        text = (query or "").strip()
        if not text:
            return {"ok": False, "message": self._t("Please type a command.")}

        parsed = self._parse_query(text)
        if not parsed:
            return {
                "ok": False,
                "message": self._t(
                    "I could not parse that query. Example: Show me all sales in Istanbul above 200000."
                ),
            }
        return {"ok": True, "action": parsed}

    def _t(self, msg):
        if request and getattr(request, "env", None):
            return request.env._(msg)
        return msg

    def _parse_query(self, text):
        lower = text.lower()

        sales_match = re.search(
            r"sales?\s+in\s+([a-zA-Z0-9\s\-_]+?)\s+(?:above|over)\s+\$?([0-9][0-9,\.]*)",
            lower,
        )
        if sales_match:
            city = sales_match.group(1).strip().title()
            amount = float(sales_match.group(2).replace(",", ""))
            return {
                "type": "ir.actions.act_window",
                "name": self._t("Sales"),
                "res_model": "propertio.sale",
                "view_mode": "list,form",
                "domain": [
                    ["project_id.city", "ilike", city],
                    ["sale_price", ">", amount],
                ],
                "target": "current",
            }

        if "all sales" in lower or "sales" in lower:
            return {
                "type": "ir.actions.act_window",
                "name": self._t("Sales"),
                "res_model": "propertio.sale",
                "view_mode": "list,form",
                "target": "current",
            }
        return None
