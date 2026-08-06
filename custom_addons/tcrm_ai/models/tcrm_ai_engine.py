# Part of TCRM AI. See LICENSE for details.

import json
import logging
import re
import time
import uuid

from tcrm import models, fields, _

from ..services import entitlement as entitlement_svc
from ..services.constants import (
    CODE_TO_STATUS,
    DEFAULT_GROQ_MODEL,
    GROQ_BASE_URL,
    SAFE_ERROR_CODES,
    rate_limit_user_message,
)
from ..services.groq_provider import GroqProviderError, GroqProviderService, trim_messages
from ..services.rate_limit import RateLimitError, check_and_consume
from ..services.tools import TcrmAiToolExecutor

_logger = logging.getLogger(__name__)

_GREETING_RE = re.compile(
    r'^\s*(merhaba|selam|selamlar|iyi\s*günler|iyi\s*akşamlar|iyi\s*sabahlar|'
    r'hey|hi|hello|good\s*(morning|afternoon|evening)|günaydın|naber|nasılsın|'
    r'nasilsin)\s*[!?.…]*\s*$',
    re.I,
)


class TcrmAiEngine(models.AbstractModel):
    _name = 'tcrm.ai.engine'
    _description = 'TCRM AI Engine'

    def _new_correlation_id(self, provided=None):
        if provided and isinstance(provided, str) and provided.strip():
            return provided.strip()[:64]
        return uuid.uuid4().hex

    def _system_prompt(self, config, lang='tr'):
        internet = bool(getattr(config, 'allow_internet_research', False))
        if lang == 'en':
            parts = [
                "You are TCRM AI — a helpful real-estate CRM assistant.",
                "Greet users warmly. For simple greetings (hi/hello), reply briefly and offer help "
                "with TCRM data, reports, or current public information — do not refuse.",
                "Answer ordinary non-sensitive questions helpfully.",
                "Use approved tools for CRM, sales, property, payments, partners, marketing "
                "and call-center data. Prefer aggregate_business_records / get_lead_summary "
                "for counts and totals.",
                "For current public facts (weather, news) call get_weather or web_search when enabled.",
                "Never invent financial totals — use tool results.",
                "Never request, reveal, or guess passwords, API keys, tokens, database "
                "credentials, encryption secrets, or shell/SQL access.",
                "Refuse only genuinely unauthorized or unsafe requests "
                "(other tenants, secrets, SQL/shell). Do not say you cannot help for ordinary questions.",
                "Distinguish TCRM business data vs internet sources; cite internet URLs.",
            ]
            if internet:
                parts.append(
                    "For weather always call get_weather and report its summary with the source URL. "
                    "Use web_search for news/facts."
                )
            else:
                parts.append(
                    "Live weather/news research is disabled; say so politely when asked."
                )
            parts.append("Answer in English unless the user writes Turkish.")
            return ' '.join(parts)
        parts = [
            "Sen TCRM AI’sın — yardımcı bir gayrimenkul CRM asistanısın.",
            "Kullanıcıyı sıcak karşıl. Basit selamlaşmalarda (merhaba/selam) kısa ve doğal "
            "yanıt ver; TCRM verileri, raporlar veya güncel bilgiler konusunda yardım teklif et. "
            "Sıradan selamlaşmayı reddetme.",
            "Hassas olmayan sıradan sorulara yardımcı ol.",
            "CRM, satış, proje, ödeme, kişi, pazarlama ve çağrı merkezi verisi için onaylı araçları kullan. "
            "Sayı/toplam için aggregate_business_records veya get_lead_summary tercih et.",
            "Güncel kamu bilgisi (hava, haber) için etkinse get_weather veya web_search çağır.",
            "Ödeme ve tutarları asla uydurma; araç sonuçlarındaki kesin değerleri kullan.",
            "Şifre, API anahtarı, token, veritabanı bilgisi, gizliler veya SQL/kabuk erişimi isteme, ifşa etme.",
            "Yalnızca gerçekten yetkisiz veya güvensiz istekleri reddet "
            "(diğer tenant, gizliler, SQL/kabuk). Sıradan sorularda “yardımcı olamam” deme.",
            "TCRM verileri ile İnternet kaynaklarını ayırt et; internet cevaplarında kaynak URL belirt.",
        ]
        if internet:
            parts.append(
                "Hava durumu sorularında mutlaka get_weather aracını çağır ve dönen özeti kaynak URL ile aktar. "
                "Genel bilgi/haber için web_search kullan. Araç sonucu geldiyse “ulaşamadım” deme."
            )
        else:
            parts.append(
                "Canlı hava/haber araştırması kapalıysa bunu nazikçe belirt."
            )
        parts.append("Kullanıcı Türkçe soruyorsa Türkçe yanıtla.")
        return ' '.join(parts)

    def _error_result(self, code, answer=None, *, correlation_id=None, retry_after=None, conversation_id=None, disabled=False):
        status = CODE_TO_STATUS.get(code, 'internal_error')
        msg = answer or SAFE_ERROR_CODES.get(code, SAFE_ERROR_CODES['unknown'])
        if code in ('rate_limited', 'quota_exceeded') and retry_after is not None:
            msg = rate_limit_user_message(retry_after)
        return {
            'success': False,
            'status': status,
            'error': True,
            'error_code': code,
            'answer': msg,
            'tables': [],
            'links': [],
            'citations': [],
            'correlation_id': correlation_id,
            'retry_after': retry_after,
            'conversation_id': conversation_id,
            'disabled': disabled,
        }

    def _success_result(self, **kwargs):
        out = {
            'success': True,
            'status': 'success',
            'error': False,
            'error_code': None,
            'tables': [],
            'links': [],
            'citations': [],
        }
        out.update(kwargs)
        # Never expose provider diagnostics / keys to chat clients.
        out.pop('api_key', None)
        out.pop('api_key_masked', None)
        return out

    def _ensure_conversation(self, conversation_id=None, session_id=None, lang='tr', source='assistant'):
        Conv = self.env['tcrm.ai.assistant.conversation']
        if conversation_id:
            conv = Conv.browse(int(conversation_id))
            if conv.exists() and (conv.user_id == self.env.user or self.env.user.has_group('base.group_system')):
                return conv
        name = _('Yeni Sohbet')
        if session_id:
            existing = Conv.search([
                ('user_id', '=', self.env.user.id),
                ('company_id', '=', self.env.company.id),
                ('name', '=', 'session:%s' % session_id),
            ], limit=1)
            if existing:
                return existing
            name = 'session:%s' % session_id
        vals = {
            'name': name,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'language': lang,
        }
        if 'source_type' in Conv._fields:
            vals['source_type'] = source
        return Conv.create(vals)

    def _store_message(self, conversation, role, content, **kwargs):
        if not conversation or not conversation.env['tcrm.ai.config'].get_config().save_conversation_history:
            return self.env['tcrm.ai.assistant.message']
        vals = {
            'conversation_id': conversation.id,
            'role': role,
            'content': (content or '')[:20000],
            'tool_calls_json': kwargs.get('tool_calls_json'),
            'tool_name': kwargs.get('tool_name'),
            'referenced_records': kwargs.get('referenced_records'),
            'prompt_tokens': kwargs.get('prompt_tokens') or 0,
            'completion_tokens': kwargs.get('completion_tokens') or 0,
            'total_tokens': kwargs.get('total_tokens') or 0,
            'provider': kwargs.get('provider'),
            'model': kwargs.get('model'),
        }
        if 'correlation_id' in self.env['tcrm.ai.assistant.message']._fields:
            vals['correlation_id'] = kwargs.get('correlation_id')
        msg = self.env['tcrm.ai.assistant.message'].create(vals)
        conversation.write({
            'last_message_date': fields.Datetime.now(),
            'total_tokens': conversation.total_tokens + (kwargs.get('total_tokens') or 0),
        })
        return msg

    def _history_messages(self, conversation, limit=16):
        if not conversation:
            return []
        msgs = conversation.message_ids.sorted('id')[-limit:]
        out = []
        for m in msgs:
            if m.role == 'tool':
                out.append({
                    'role': 'tool',
                    'tool_call_id': (m.tool_name or 'tool')[:40],
                    'content': m.content or '',
                })
            else:
                item = {'role': m.role, 'content': m.content or ''}
                if m.tool_calls_json:
                    try:
                        item['tool_calls'] = json.loads(m.tool_calls_json)
                    except Exception:
                        pass
                out.append(item)
        return out

    def _greeting_reply(self, lang='tr'):
        if lang == 'en':
            return (
                "Hello! How can I help with your TCRM data, reports, "
                "or current public information?"
            )
        return (
            "Merhaba! TCRM verileriniz, raporlarınız veya güncel bilgiler "
            "konusunda nasıl yardımcı olabilirim?"
        )

    def _ask(self, message, base_url=None, correlation_id=None, source='assistant'):
        """
        Unified TCRM AI orchestration (Groq + approved tools).

        All entry points (full page, floating widget, Discuss bot, CRM buttons)
        must call this method.
        """
        env = self.env
        cid = self._new_correlation_id(correlation_id)
        if base_url is None:
            base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')

        session_id = None
        conversation_id = None
        text = message
        disable_tools = False
        if isinstance(message, dict):
            text = message.get('text') or message.get('message') or ''
            session_id = message.get('session_id')
            conversation_id = message.get('conversation_id')
            cid = self._new_correlation_id(message.get('correlation_id') or cid)
            source = message.get('source') or source
            disable_tools = bool(message.get('disable_tools'))
        text = (text or '').strip()
        if not text:
            return self._error_result(
                'invalid_configuration',
                _('Lütfen bir soru yazın.'),
                correlation_id=cid,
            )

        config = env['tcrm.ai.config'].sudo().get_config()
        block = entitlement_svc.chat_block_reason(env)
        if block:
            return self._error_result(
                'entitlement_denied' if 'etkin değil' in (block or '') else 'forbidden',
                block,
                correlation_id=cid,
                disabled=True,
            )

        try:
            check_and_consume(env, config)
        except RateLimitError as exc:
            return self._error_result(
                'rate_limited',
                exc.safe_message,
                correlation_id=cid,
                retry_after=getattr(exc, 'retry_after', 15),
            )

        lang = config.default_language or 'tr'
        if any(ch in text.lower() for ch in (' the ', ' what ', ' how ', ' show ', 'hello', ' hi ')):
            lang = 'en'
        if _GREETING_RE.match(text) or text.lower() in ('merhaba', 'selam', 'hi', 'hello'):
            lang = 'en' if text.lower() in ('hi', 'hello') else 'tr'

        conversation = self._ensure_conversation(
            conversation_id, session_id, lang=lang, source=source,
        )

        # Fast-path greetings: no Groq round-trip, same conversation store.
        if _GREETING_RE.match(text):
            answer = self._greeting_reply(lang)
            self._store_message(conversation, 'user', text, correlation_id=cid)
            self._store_message(conversation, 'assistant', answer, correlation_id=cid)
            _logger.info('TCRM AI greeting cid=%s db=%s user=%s', cid, env.cr.dbname, env.user.id)
            return self._success_result(
                answer=answer,
                conversation_id=conversation.id,
                correlation_id=cid,
                tools_used=[],
                usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            )

        usage_rec = env['tcrm.ai.usage'].sudo().start_request(conversation)
        if hasattr(usage_rec, 'correlation_id'):
            try:
                usage_rec.sudo().write({'correlation_id': cid})
            except Exception:
                pass
        started = time.monotonic()

        key = config._ensure_valid_groq_key() if hasattr(config, '_ensure_valid_groq_key') else config._get_plaintext_api_key()
        if not key:
            usage_rec.finish(success=False, error_code='config_missing', duration_ms=0)
            return self._error_result('config_missing', correlation_id=cid, conversation_id=conversation.id)

        executor = TcrmAiToolExecutor(env, config, base_url=base_url, correlation_id=cid)
        tools = [] if disable_tools else executor.available_tool_defs()
        service = GroqProviderService(
            api_key=key,
            base_url=config.base_url or GROQ_BASE_URL,
            model=config.model or DEFAULT_GROQ_MODEL,
            timeout=config.request_timeout or 45,
            max_retries=1,
            correlation_id=cid,
        )

        self._store_message(conversation, 'user', text, correlation_id=cid)
        if disable_tools or source == 'html_editor':
            sys_prompt = (
                "You are TCRM AI writing assistant. Produce clear, ready-to-insert text. "
                "No tools, no secrets, no SQL. Match the user's language. "
                "Return only the requested content without meta commentary."
                if lang == 'en' else
                "Sen TCRM AI yazım asistanısın. Açık, doğrudan eklenebilir metin üret. "
                "Araç kullanma, gizlileri ifşa etme. Kullanıcının dilinde yanıt ver. "
                "Yalnızca istenen içeriği yaz; meta açıklama ekleme."
            )
        else:
            sys_prompt = self._system_prompt(config, lang)
        messages = [{'role': 'system', 'content': sys_prompt}]
        messages.extend(self._history_messages(conversation, limit=12))
        if not messages or messages[-1].get('role') != 'user':
            messages.append({'role': 'user', 'content': text})
        messages = trim_messages(messages, max_messages=18)

        tables = []
        links = []
        citations = []
        total_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        max_rounds = max(1, min(12, config.max_tool_calls or 8))

        try:
            for _round in range(max_rounds):
                result = service.chat_completions(
                    messages,
                    tools=tools or None,
                    max_tokens=config.max_output_tokens or 2048,
                    temperature=config.temperature if config.temperature is not None else 0.3,
                )
                for k in total_usage:
                    total_usage[k] += int((result.get('usage') or {}).get(k) or 0)

                tool_calls = result.get('tool_calls') or []
                if tool_calls:
                    messages.append({
                        'role': 'assistant',
                        'content': result.get('text') or '',
                        'tool_calls': tool_calls,
                    })
                    self._store_message(
                        conversation, 'assistant', result.get('text') or '',
                        tool_calls_json=json.dumps(tool_calls),
                        correlation_id=cid,
                        **{kk: total_usage[kk] for kk in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
                    )
                    for tc in tool_calls:
                        fn = tc.get('function') or {}
                        name = fn.get('name') or ''
                        raw_args = fn.get('arguments') or '{}'
                        try:
                            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                        except Exception:
                            args = {}
                        _logger.info(
                            'TCRM AI tool_call cid=%s tool=%s', cid, name,
                        )
                        try:
                            tool_result = executor.execute(name, args)
                        except Exception as tool_exc:
                            tool_result = json.dumps({'error': str(getattr(tool_exc, 'message', tool_exc))})
                        try:
                            parsed = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
                        except Exception:
                            parsed = {'raw': tool_result}
                        if isinstance(parsed, dict):
                            if parsed.get('rows') and isinstance(parsed['rows'], list) and parsed['rows']:
                                headers = list(parsed['rows'][0].keys())
                                tables.append({
                                    'headers': headers,
                                    'rows': [[r.get(h, '') for h in headers] for r in parsed['rows']],
                                })
                            for ln in parsed.get('links') or []:
                                if ln not in links:
                                    links.append(ln)
                            for cite in parsed.get('citations') or []:
                                if cite and cite not in citations:
                                    citations.append(cite)
                        messages.append({
                            'role': 'tool',
                            'tool_call_id': tc.get('id') or name,
                            'content': tool_result if isinstance(tool_result, str) else json.dumps(tool_result),
                        })
                        self._store_message(
                            conversation, 'tool',
                            tool_result if isinstance(tool_result, str) else json.dumps(tool_result),
                            tool_name=name,
                            correlation_id=cid,
                            referenced_records=json.dumps(executor.references[-5:], default=str),
                        )
                    continue

                answer = (result.get('text') or '').strip() or _('Yanıt alınamadı.')
                # Soft-guard: model still refuses after greeting-like content.
                if re.search(r'yardımcı olamam|cannot help|i can.?t help', answer, re.I) and len(text) < 40:
                    answer = self._greeting_reply(lang)
                self._store_message(
                    conversation, 'assistant', answer,
                    correlation_id=cid,
                    referenced_records=json.dumps(executor.references, default=str),
                    **total_usage,
                )
                duration = int((time.monotonic() - started) * 1000)
                usage_rec.finish(
                    usage=total_usage,
                    duration_ms=duration,
                    tools=executor.tools_used,
                    success=True,
                    provider='groq',
                    model=result.get('model'),
                )
                _logger.info(
                    'TCRM AI ok cid=%s db=%s tools=%s ms=%s',
                    cid, env.cr.dbname, executor.tools_used, duration,
                )
                return self._success_result(
                    answer=answer,
                    tables=tables,
                    links=links or [r for r in executor.references if r.get('url')],
                    citations=citations or [
                        r for r in executor.references if r.get('source_type') == 'internet'
                    ],
                    conversation_id=conversation.id,
                    correlation_id=cid,
                    usage=total_usage,
                    tools_used=executor.tools_used,
                )

            messages.append({
                'role': 'user',
                'content': 'Provide the final answer now using tool results. Do not call more tools.',
            })
            result = service.chat_completions(
                trim_messages(messages, 20),
                tools=None,
                max_tokens=config.max_output_tokens or 2048,
                temperature=0.2,
            )
            for k in total_usage:
                total_usage[k] += int((result.get('usage') or {}).get(k) or 0)
            answer = (result.get('text') or '').strip() or _('Araç limiti doldu; kısmi sonuçlar yukarıda.')
            duration = int((time.monotonic() - started) * 1000)
            usage_rec.finish(
                usage=total_usage, duration_ms=duration, tools=executor.tools_used,
                success=True, provider='groq', model=result.get('model'),
            )
            self._store_message(conversation, 'assistant', answer, correlation_id=cid, **total_usage)
            return self._success_result(
                answer=answer,
                tables=tables,
                links=links or [r for r in executor.references if r.get('url')],
                citations=citations,
                conversation_id=conversation.id,
                correlation_id=cid,
                usage=total_usage,
                tools_used=executor.tools_used,
            )
        except GroqProviderError as exc:
            duration = int((time.monotonic() - started) * 1000)
            usage_rec.finish(success=False, error_code=exc.code, duration_ms=duration, tools=executor.tools_used)
            _logger.warning(
                'TCRM AI provider_error cid=%s code=%s status=%s',
                cid, exc.code, exc.http_status,
            )
            if exc.code in ('quota_exceeded', 'rate_limited'):
                config.sudo().write({'last_safe_error': exc.safe_message})
            else:
                config.sudo().write({
                    'last_safe_error': exc.safe_message,
                    'last_connection_status': 'error',
                })
            return self._error_result(
                exc.code,
                exc.safe_message,
                correlation_id=cid,
                retry_after=exc.retry_after,
                conversation_id=conversation.id,
            )
        except Exception:
            _logger.exception('TCRM AI ask failed cid=%s db=%s', cid, env.cr.dbname)
            duration = int((time.monotonic() - started) * 1000)
            usage_rec.finish(success=False, error_code='internal_error', duration_ms=duration)
            return self._error_result('internal_error', correlation_id=cid, conversation_id=conversation.id)

    def _format_answer_as_html(self, result):
        """HTML body for Discuss / mail.bot replies."""
        from markupsafe import Markup, escape
        if not isinstance(result, dict):
            return Markup(str(result or ''))
        parts = [str(escape(result.get('answer') or '')).replace('\n', '<br/>')]
        for tbl in result.get('tables') or []:
            headers = tbl.get('headers') or []
            rows = tbl.get('rows') or []
            if not headers:
                continue
            parts.append('<table border="1" cellpadding="4" style="border-collapse:collapse;margin:8px 0;">')
            parts.append('<tr>' + ''.join('<th>%s</th>' % escape(str(h)) for h in headers) + '</tr>')
            for row in rows[:30]:
                cells = row if isinstance(row, (list, tuple)) else [row.get(h, '') for h in headers]
                parts.append('<tr>' + ''.join('<td>%s</td>' % escape('' if c is None else str(c)) for c in cells) + '</tr>')
            parts.append('</table>')
        for link in (result.get('citations') or result.get('links') or []):
            url = link.get('url') or ''
            label = link.get('label') or link.get('title') or url
            if url:
                parts.append('<div><a href="%s" target="_blank" rel="noopener">%s</a></div>' % (
                    escape(url), escape(label),
                ))
        return Markup(''.join(parts))

    def _test_provider_keys(self, provider):
        """Legacy helper used by provider form; uses Groq path when applicable."""
        results = []
        for key in provider.key_ids.filtered('active'):
            try:
                from ..services.crypto import decrypt_secret
                plain = decrypt_secret(self.env, key.api_key) if str(key.api_key or '').startswith('enc:v1:') else (key.api_key or '')
                if provider.provider_code == 'groq':
                    svc = GroqProviderService(api_key=plain, model=DEFAULT_GROQ_MODEL, timeout=20, max_retries=0)
                    svc.test_connection()
                    results.append((key.name, True, ''))
                else:
                    results.append((key.name, False, 'Only Groq test supported in this release'))
            except Exception as exc:
                results.append((key.name, False, str(getattr(exc, 'safe_message', type(exc).__name__))))
        return results
