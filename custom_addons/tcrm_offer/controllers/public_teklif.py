# -*- coding: utf-8 -*-
import json
import logging

from tcrm import http, _
from tcrm.http import request
from tcrm.exceptions import UserError

from ..services import pricing as pricing_svc
from ..services import rate_limit
from ..services import tokens as token_svc

_logger = logging.getLogger(__name__)


class PublicTeklifController(http.Controller):
    """Public passcode-gated offer experience at /teklif/<token>."""

    SESSION_KEY = 'teklif_unlock'
    SESSION_TOKEN_KEY = 'teklif_session_token'

    def _client_ip(self):
        return (
            request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.httprequest.remote_addr
            or ''
        )

    def _ua(self):
        return (request.httprequest.user_agent.string or '')[:255]

    def _find_offer(self, token):
        return request.env['tcrm.offer']._find_by_public_token(token)

    def _unlocked(self, token):
        unlock = request.session.get(self.SESSION_KEY) or {}
        return bool(unlock.get(token))

    def _set_unlocked(self, token, session_raw=None):
        # Reassign top-level keys so the session store persists nested changes.
        unlock = dict(request.session.get(self.SESSION_KEY) or {})
        unlock[token] = True
        request.session[self.SESSION_KEY] = unlock
        if session_raw:
            tokens = dict(request.session.get(self.SESSION_TOKEN_KEY) or {})
            tokens[token] = session_raw
            request.session[self.SESSION_TOKEN_KEY] = tokens
        request.session.touch()

    def _closed_response(self, reason='closed'):
        return request.render('tcrm_offer.public_teklif_closed', {
            'reason': reason,
        }, status=403)

    def _json(self, payload, status=200):
        return request.make_json_response(payload, status=status)

    # ------------------------------------------------------------------
    # GET /teklif/<token>
    # ------------------------------------------------------------------
    @http.route(
        '/teklif/<string:token>',
        type='http',
        auth='public',
        website=True,
        methods=['GET'],
        sitemap=False,
    )
    def teklif_view(self, token, **kw):
        offer = self._find_offer(token)
        if not offer:
            # Do not leak whether token existed
            return self._closed_response('unavailable')

        if offer.status in ('expired',) or (
            offer.valid_until and offer.valid_until < fields_today()
        ):
            if offer.status not in ('expired', 'closed', 'revoked'):
                try:
                    offer.sudo().write({'status': 'expired'})
                except Exception:  # noqa: BLE001
                    pass
            return self._closed_response('expired')

        if offer.status in ('draft', 'paused', 'revoked', 'closed'):
            return self._closed_response(offer.status)

        if not self._unlocked(token):
            return request.render('tcrm_offer.public_teklif_passcode', {
                'token': token,
                'error': False,
            })

        # Touch session
        payload = offer.get_public_payload()
        default_selected = [
            i['id'] for i in payload['items']
            if i.get('default_selected') or i.get('selection_type') == 'required'
        ]
        quote = offer.action_preview_quote(
            selected_ids=default_selected,
            ad_budget=offer.ad_budget_default,
        )
        return request.render('tcrm_offer.public_teklif_view', {
            'token': token,
            'offer': offer,
            'payload': payload,
            'payload_json': json.dumps(payload, ensure_ascii=False, default=str),
            'default_selected': default_selected,
            'quote': quote,
            'format_try': pricing_svc.format_try,
            'from_kurus': pricing_svc.from_kurus,
            'readonly': not offer.public_is_selectable(),
            'approval': offer.approval_id,
        })

    # ------------------------------------------------------------------
    # POST /teklif/<token>/unlock
    # ------------------------------------------------------------------
    @http.route(
        '/teklif/<string:token>/unlock',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
        sitemap=False,
    )
    def teklif_unlock(self, token, **post):
        offer = self._find_offer(token)
        if not offer or not offer.public_is_accessible():
            return self._closed_response('unavailable')

        ip = self._client_ip()
        rl_key = f'teklif:{token}:{ip}'
        if not rate_limit.allow(rl_key, limit=10, window_seconds=300):
            return request.render('tcrm_offer.public_teklif_passcode', {
                'token': token,
                'error': _('Çok fazla deneme. Lütfen daha sonra tekrar deneyin.'),
            })

        passcode = (post.get('passcode') or '').strip().upper()
        if not offer.verify_passcode(passcode, ip=ip):
            return request.render('tcrm_offer.public_teklif_passcode', {
                'token': token,
                'error': _('Passcode hatalı veya erişim geçici olarak kilitli.'),
            })

        session_raw = offer.create_access_session(ip=ip, user_agent=self._ua())
        self._set_unlocked(token, session_raw)
        offer.mark_viewed(ip=ip)
        rate_limit.clear(rl_key)
        return request.redirect(f'/teklif/{token}')

    # ------------------------------------------------------------------
    # POST /teklif/<token>/quote  (JSON)
    # ------------------------------------------------------------------
    @http.route(
        '/teklif/<string:token>/quote',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
        sitemap=False,
    )
    def teklif_quote(self, token, **post):
        offer = self._find_offer(token)
        if not offer or not self._unlocked(token):
            return self._json({'error': 'unauthorized'}, status=401)
        if not offer.public_is_accessible():
            return self._json({'error': 'closed'}, status=403)

        try:
            body = request.httprequest.get_json(force=True, silent=True) or {}
        except Exception:  # noqa: BLE001
            body = {}
        if not body and post:
            body = post

        selected = body.get('selected_ids') or []
        if isinstance(selected, str):
            selected = json.loads(selected)
        selected = [int(x) for x in selected]
        ad_budget = float(body.get('ad_budget') or offer.ad_budget_default or 0)

        # Clamp budget
        ad_budget = max(offer.ad_budget_min or 0, min(offer.ad_budget_max or ad_budget, ad_budget))

        try:
            quote = offer.action_preview_quote(selected_ids=selected, ad_budget=ad_budget)
        except ValueError as exc:
            return self._json({'error': str(exc)}, status=400)

        return self._json({
            'ok': True,
            'net': float(pricing_svc.from_kurus(quote['net_kurus'])),
            'tax': float(pricing_svc.from_kurus(quote['tax_kurus'])),
            'gross': float(pricing_svc.from_kurus(quote['gross_kurus'])),
            'monthly_net': float(pricing_svc.from_kurus(quote['monthly']['net'])),
            'one_time_net': float(pricing_svc.from_kurus(quote['one_time']['net'])),
            'per_session_net': float(pricing_svc.from_kurus(quote['per_session']['net'])),
            'net_fmt': pricing_svc.format_try(quote['net_kurus']),
            'tax_fmt': pricing_svc.format_try(quote['tax_kurus']),
            'gross_fmt': pricing_svc.format_try(quote['gross_kurus']),
            'monthly_fmt': pricing_svc.format_try(quote['monthly']['net']),
            'one_time_fmt': pricing_svc.format_try(quote['one_time']['net']),
            'per_session_fmt': pricing_svc.format_try(quote['per_session']['net']),
            'lines': [
                {
                    'id': l['id'],
                    'name': l['name'],
                    'billing_period': l['billing_period'],
                    'net': float(pricing_svc.from_kurus(l['net_kurus'])),
                    'net_fmt': pricing_svc.format_try(l['net_kurus']),
                }
                for l in quote['lines']
            ],
            'tax_rate': quote['tax_rate_percent'],
        })

    # ------------------------------------------------------------------
    # POST /teklif/<token>/approve
    # ------------------------------------------------------------------
    @http.route(
        '/teklif/<string:token>/approve',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
        sitemap=False,
    )
    def teklif_approve(self, token, **post):
        offer = self._find_offer(token)
        if not offer or not self._unlocked(token):
            return self._json({'error': 'unauthorized'}, status=401)
        if not offer.public_is_selectable():
            return self._json({'error': 'not_selectable'}, status=403)

        try:
            body = request.httprequest.get_json(force=True, silent=True) or {}
        except Exception:  # noqa: BLE001
            body = {}
        if not body:
            body = dict(post)

        selected = body.get('selected_ids') or []
        if isinstance(selected, str):
            selected = json.loads(selected)
        selected = [int(x) for x in selected]
        ad_budget = float(body.get('ad_budget') or offer.ad_budget_default or 0)

        try:
            approval = offer.action_approve_public(
                selected_ids=selected,
                ad_budget=ad_budget,
                approver_name=(body.get('approver_name') or '').strip(),
                approver_email=(body.get('approver_email') or '').strip(),
                approver_company=(body.get('approver_company') or '').strip(),
                approver_phone=(body.get('approver_phone') or '').strip(),
                accepted_services=bool(body.get('accepted_services')),
                accepted_terms=bool(body.get('accepted_terms')),
                accepted_kvkk=bool(body.get('accepted_kvkk')),
                idempotency_key=(body.get('idempotency_key') or '').strip() or None,
                ip=self._client_ip(),
                user_agent=self._ua(),
            )
        except UserError as exc:
            return self._json({'error': str(exc)}, status=400)
        except Exception:  # noqa: BLE001
            _logger.exception('Approve failed')
            return self._json({'error': 'server_error'}, status=500)

        return self._json({
            'ok': True,
            'redirect': f'/teklif/{token}/receipt',
            'approval_id': approval.id,
            'gross': approval.gross_total,
        })

    # ------------------------------------------------------------------
    # GET /teklif/<token>/receipt
    # ------------------------------------------------------------------
    @http.route(
        '/teklif/<string:token>/receipt',
        type='http',
        auth='public',
        website=True,
        methods=['GET'],
        sitemap=False,
    )
    def teklif_receipt(self, token, **kw):
        offer = self._find_offer(token)
        if not offer or not self._unlocked(token):
            return self._closed_response('unavailable')
        if not offer.approval_id:
            return request.redirect(f'/teklif/{token}')
        return request.render('tcrm_offer.public_teklif_receipt', {
            'offer': offer,
            'approval': offer.approval_id,
            'format_try': pricing_svc.format_try,
            'to_kurus': pricing_svc.to_kurus,
        })


def fields_today():
    from tcrm import fields
    return fields.Date.context_today(request.env['tcrm.offer'])
