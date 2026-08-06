/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useEffect, useRef, useState } from "@tcrm/owl";

export class TcrmAiChat extends Component {
    static template = "tcrm_ai.TcrmAiChat";
    static props = { ...standardActionServiceProps };

    setup() {
        this.ai = useService("tcrm_ai");
        this.user = user;
        this.messagesRef = useRef("messages");
        const sessionId =
            (typeof crypto !== "undefined" && crypto.randomUUID && crypto.randomUUID()) ||
            "tcrm-ai-" + Date.now() + "-" + Math.random().toString(36).slice(2);
        this.state = useState({
            message: "",
            loading: false,
            history: [],
            conversations: [],
            sessionId,
            conversationId: null,
            status: null,
            disabledReason: "",
            sidebarOpen: true,
            lastFailedText: "",
        });
        onWillStart(async () => {
            await this.refreshStatus();
            await this.refreshConversations();
        });
        useEffect(
            () => {
                const el = this.messagesRef.el;
                if (el) {
                    el.scrollTop = el.scrollHeight;
                }
            },
            () => [this.state.history.length, this.state.loading]
        );
    }

    get placeholder() {
        return _t("Bir mesaj yazın…");
    }

    get chatEnabled() {
        return !!(this.state.status && this.state.status.chat_enabled);
    }

    get userName() {
        return this.user?.name || _t("Siz");
    }

    async refreshStatus() {
        try {
            const status = await this.ai.getStatus();
            this.state.status = status;
            this.state.disabledReason = status.chat_disabled_reason || "";
        } catch (e) {
            this.state.disabledReason = _t("TCRM AI durumu alınamadı.");
        }
    }

    async refreshConversations() {
        try {
            const res = await this.ai.listConversations(50);
            this.state.conversations = res.conversations || [];
        } catch (e) {
            this.state.conversations = [];
        }
    }

    async selectConversation(id) {
        if (!id || this.state.loading) {
            return;
        }
        this.state.conversationId = id;
        this.state.history = [];
        try {
            const res = await this.ai.getMessages(id);
            this.state.history = (res.messages || []).map((m) => {
                if (m.role === "user") {
                    return { role: "user", content: m.content, create_date: m.create_date };
                }
                return {
                    role: "assistant",
                    answer: m.content,
                    tables: [],
                    links: [],
                    citations: [],
                    error: false,
                    create_date: m.create_date,
                };
            });
        } catch (e) {
            this.state.history = [];
        }
    }

    async onNewConversation() {
        if (this.state.loading) {
            return;
        }
        try {
            const res = await this.ai.newConversation("assistant");
            this.state.conversationId = res.conversation_id;
            this.state.history = [];
            this.state.message = "";
            await this.refreshConversations();
        } catch (e) {
            this.state.conversationId = null;
            this.state.history = [];
        }
    }

    async onSend(textOverride) {
        const text = (textOverride || this.state.message || "").trim();
        if (!text || this.state.loading) {
            return;
        }
        if (!this.chatEnabled) {
            this.state.history.push({
                role: "assistant",
                answer: this.state.disabledReason || _t("TCRM AI kullanılamıyor."),
                tables: [],
                links: [],
                citations: [],
                error: true,
                status: "forbidden",
            });
            return;
        }
        this.state.history.push({
            role: "user",
            content: text,
            create_date: new Date().toISOString(),
        });
        if (!textOverride) {
            this.state.message = "";
        }
        this.state.loading = true;
        this.state.lastFailedText = "";
        const RPC_TIMEOUT_MS = 90000;
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error(_t("İstek zaman aşımına uğradı."))), RPC_TIMEOUT_MS)
        );
        try {
            const result = await Promise.race([
                this.ai.ask({
                    message: text,
                    sessionId: this.state.sessionId,
                    conversationId: this.state.conversationId,
                    source: "assistant",
                }),
                timeoutPromise,
            ]);
            if (result.conversation_id) {
                this.state.conversationId = result.conversation_id;
            }
            const failed = !!(result.error || result.success === false);
            if (failed) {
                this.state.lastFailedText = text;
            }
            this.state.history.push({
                role: "assistant",
                answer: this.ai.formatRetryMessage(result) || result.answer || "",
                tables: result.tables || [],
                links: result.links || [],
                citations: result.citations || [],
                error: failed,
                status: result.status || (failed ? "internal_error" : "success"),
                retry_after: result.retry_after,
                create_date: new Date().toISOString(),
            });
            await this.refreshConversations();
        } catch (e) {
            this.state.lastFailedText = text;
            this.state.history.push({
                role: "assistant",
                answer: _t("Hata: ") + (e.message || String(e)),
                tables: [],
                links: [],
                citations: [],
                error: true,
                status: "timeout",
            });
        } finally {
            this.state.loading = false;
        }
    }

    onRetry() {
        if (this.state.lastFailedText) {
            this.onSend(this.state.lastFailedText);
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.onSend();
        }
    }

    openLink(url) {
        if (url && url.startsWith("http")) {
            window.open(url, "_blank", "noopener");
        }
    }

    formatTime(iso) {
        if (!iso) {
            return "";
        }
        try {
            const d = new Date(iso);
            return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (e) {
            return "";
        }
    }

    async onCopy(item) {
        const parts = [item.answer || ""];
        if (item.tables && item.tables.length) {
            for (const tbl of item.tables) {
                parts.push((tbl.headers || []).join("\t"));
                for (const row of tbl.rows || []) {
                    parts.push(row && row.join ? row.join("\t") : Object.values(row || {}).join("\t"));
                }
            }
        }
        try {
            await navigator.clipboard.writeText(parts.join("\n\n"));
        } catch (e) {
            console.warn("Clipboard copy failed", e);
        }
    }

    async onExport(item, format) {
        if (!item.tables || !item.tables.length) {
            return;
        }
        const response = await fetch("/tcrm_ai/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ format, tables: item.tables, title: "TCRM AI Report" }),
            credentials: "same-origin",
        });
        if (!response.ok) {
            return;
        }
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        if (format === "xlsx") {
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = "tcrm_ai_report.xlsx";
            a.click();
            URL.revokeObjectURL(blobUrl);
        } else {
            window.open(blobUrl, "_blank");
        }
    }

    toggleSidebar() {
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }
}

registry.category("actions").add("tcrm_ai.chat", TcrmAiChat);
