/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Component, useState } from "@tcrm/owl";

export class TcrmAiChat extends Component {
    static template = "tcrm_ai.TcrmAiChat";
    static props = { ...standardActionServiceProps };

    setup() {
        const sessionId =
            (typeof crypto !== "undefined" && crypto.randomUUID && crypto.randomUUID()) ||
            "tcrm-ai-" + Date.now() + "-" + Math.random().toString(36).slice(2);
        this.state = useState({
            message: "",
            loading: false,
            history: [],
            sessionId,
        });
    }

    get placeholder() {
        return "Ask anything: payment plan for a client, sales report, or general question…";
    }

    async onSend() {
        const text = (this.state.message || "").trim();
        if (!text || this.state.loading) return;
        this.state.history.push({ role: "user", content: text });
        this.state.message = "";
        this.state.loading = true;
        const RPC_TIMEOUT_MS = 90000; // 90s - backend adapters timeout at 45s per call
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error("Request timed out. The AI service may be slow or unreachable. Check TCRM AI → AI Providers (or AI Settings) and try again.")), RPC_TIMEOUT_MS)
        );
        try {
            const result = await Promise.race([
                rpc("/tcrm_ai/ask", {
                    message: text,
                    session_id: this.state.sessionId || undefined,
                }),
                timeoutPromise,
            ]);
            this.state.history.push({
                role: "assistant",
                answer: result.answer || "",
                tables: result.tables || [],
                links: result.links || [],
                error: result.error,
            });
        } catch (e) {
            this.state.history.push({
                role: "assistant",
                answer: "Error: " + (e.message || String(e)),
                tables: [],
                links: [],
                error: true,
            });
        } finally {
            this.state.loading = false;
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
            window.open(url, "_blank");
        } else {
            window.location.href = url || "#";
        }
    }

    async onCopy(item) {
        const parts = [item.answer || ""];
        if (item.tables && item.tables.length) {
            for (const tbl of item.tables) {
                const headers = (tbl.headers || []).join("\t");
                parts.push(headers);
                for (const row of tbl.rows || []) {
                    parts.push((row && row.join ? row.join("\t") : Object.values(row || {}).join("\t")));
                }
            }
        }
        const text = parts.join("\n\n");
        try {
            await navigator.clipboard.writeText(text);
        } catch (e) {
            console.warn("Clipboard copy failed", e);
        }
    }

    async onExport(item, format) {
        if (!item.tables || !item.tables.length) return;
        const url = "/tcrm_ai/export";
        const body = JSON.stringify({
            format,
            tables: item.tables,
            title: "TCRM AI Report",
        });
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
            credentials: "same-origin",
        });
        if (!response.ok) return;
        const blob = await response.blob();
        const ext = format === "xlsx" ? "xlsx" : "html";
        const blobUrl = URL.createObjectURL(blob);
        if (format === "xlsx") {
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = "tcrm_ai_report." + ext;
            a.click();
            URL.revokeObjectURL(blobUrl);
        } else {
            window.open(blobUrl, "_blank");
        }
    }
}

registry.category("actions").add("tcrm_ai.chat", TcrmAiChat);
