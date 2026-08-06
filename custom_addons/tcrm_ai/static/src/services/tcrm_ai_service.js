/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

function newCorrelationId() {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return "tcrm-ai-" + Date.now() + "-" + Math.random().toString(36).slice(2);
}

/**
 * Shared backend client for full-page and floating TCRM AI assistants.
 * Both UIs must use this service — never call alternate providers from the browser.
 */
export const tcrmAiService = {
    dependencies: [],
    start() {
        return {
            newCorrelationId,

            async getStatus() {
                return rpc("/tcrm_ai/status", {});
            },

            async ask({ message, sessionId, conversationId, source = "assistant", correlationId } = {}) {
                const cid = correlationId || newCorrelationId();
                const result = await rpc("/tcrm_ai/ask", {
                    message,
                    session_id: sessionId || undefined,
                    conversation_id: conversationId || undefined,
                    correlation_id: cid,
                    source,
                });
                return { ...result, correlation_id: result?.correlation_id || cid };
            },

            async listConversations(limit = 40) {
                return rpc("/tcrm_ai/conversations", { limit });
            },

            async getMessages(conversationId) {
                return rpc("/tcrm_ai/conversation/messages", { conversation_id: conversationId });
            },

            async newConversation(source = "assistant") {
                return rpc("/tcrm_ai/conversation/new", { source });
            },

            async clearSession({ sessionId, conversationId } = {}) {
                return rpc("/tcrm_ai/clear_session", {
                    session_id: sessionId,
                    conversation_id: conversationId,
                });
            },

            formatRetryMessage(result) {
                if (!result) {
                    return "";
                }
                if (result.answer) {
                    return result.answer;
                }
                const secs = result.retry_after;
                if (result.status === "rate_limited" && secs != null) {
                    const n = Math.max(5, parseInt(secs, 10) || 5);
                    if (n < 60) {
                        return `${n} saniye sonra tekrar deneyin.`;
                    }
                    return `${Math.max(1, Math.floor(n / 60))} dakika sonra tekrar deneyin.`;
                }
                return "Bir hata oluştu.";
            },
        };
    },
};

registry.category("services").add("tcrm_ai", tcrmAiService);
