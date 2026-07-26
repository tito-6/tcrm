/** @odoo-module **/

import { Component, markup, onMounted, useRef, useState } from "@tcrm/owl";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { useService } from "@web/core/utils/hooks";
import { aiResearchService } from "../../services/ai_research_service";

function escapeHtml(text) {
    return String(text || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function safeMessageHtml(text) {
    const escaped = escapeHtml(text).replace(/\n/g, "<br/>");
    return markup(escaped);
}

export class ResearchAssistant extends Component {
    static template = "tcrm_ai_research.ResearchAssistant";
    static props = { ...standardActionServiceProps };

    setup() {
        this.notification = useService("notification");
        this.fileInput = useRef("fileInput");
        this.messagesRef = useRef("messages");
        const ctx = this.props.action?.context || {};
        this.state = useState({
            workspaces: [],
            workspaceId: ctx.workspace_id || false,
            conversationId: ctx.conversation_id || false,
            history: [],
            messages: [],
            documents: [],
            selectedDocumentIds: [],
            question: "",
            language: "tr",
            loading: false,
            error: "",
            statusText: "",
            contextLabel: ctx.record_name || "",
            crmContext: {
                partner_id: ctx.partner_id || false,
                lead_id: ctx.lead_id || false,
                res_model: ctx.res_model || false,
                res_id: ctx.res_id || false,
                record_name: ctx.record_name || false,
            },
            allowWebResearch: false,
            internalDocumentsOnly: true,
            webResearchAllowed: false,
            activeCitations: [],
            lastQuestion: "",
            publicConfig: {},
        });
        onMounted(() => this.bootstrap());
    }

    async bootstrap() {
        try {
            const [cfgRes, wsRes] = await Promise.all([
                aiResearchService.getConfig(),
                aiResearchService.listWorkspaces(),
            ]);
            if (cfgRes?.ok) {
                this.state.publicConfig = cfgRes.data || {};
                this.state.language = cfgRes.data.default_language || "tr";
                this.state.webResearchAllowed = !!cfgRes.data.enable_web_research;
            }
            if (wsRes?.ok) {
                this.state.workspaces = wsRes.data || [];
                if (!this.state.workspaceId && this.state.workspaces.length) {
                    this.state.workspaceId = this.state.workspaces[0].id;
                }
            }
            if (this.state.crmContext.res_model || this.state.crmContext.lead_id || this.state.crmContext.partner_id) {
                const preview = await aiResearchService.previewContext(this.state.crmContext);
                if (preview?.ok && preview.data?.record_name) {
                    this.state.contextLabel = preview.data.record_name;
                }
            }
            await this.refreshHistory();
            if (this.state.conversationId) {
                await this.loadConversation(this.state.conversationId);
            } else if (this.state.workspaceId) {
                await this.ensureConversation();
            }
            await this.refreshDocuments();
        } catch (e) {
            this.state.error = e.message || String(e);
        }
    }

    async refreshHistory() {
        const res = await aiResearchService.listConversations({
            workspace_id: this.state.workspaceId || undefined,
            limit: 30,
        });
        if (res?.ok) {
            this.state.history = res.data || [];
        }
    }

    async refreshDocuments() {
        if (!this.state.workspaceId) {
            this.state.documents = [];
            return;
        }
        const res = await aiResearchService.listDocuments(this.state.workspaceId);
        if (res?.ok) {
            this.state.documents = res.data || [];
        }
        if (this.state.conversationId) {
            const conv = await aiResearchService.getConversation(this.state.conversationId);
            if (conv?.ok) {
                this.state.selectedDocumentIds = conv.data.document_ids || [];
            }
        }
    }

    async ensureConversation() {
        if (this.state.conversationId || !this.state.workspaceId) {
            return;
        }
        const res = await aiResearchService.createConversation({
            workspace_id: this.state.workspaceId,
            ...this.state.crmContext,
            language: this.state.language,
        });
        if (res?.ok) {
            this.state.conversationId = res.data.id;
            this.state.messages = res.data.messages || [];
            await this.refreshHistory();
        } else {
            this.state.error = res?.error?.message || "Conversation could not be created.";
        }
    }

    async loadConversation(id) {
        const res = await aiResearchService.getConversation(id);
        if (!res?.ok) {
            this.state.error = res?.error?.message || "Conversation load failed.";
            return;
        }
        this.state.conversationId = res.data.id;
        this.state.workspaceId = res.data.workspace_id;
        this.state.messages = res.data.messages || [];
        this.state.language = res.data.language || this.state.language;
        this.state.allowWebResearch = !!res.data.allow_web_research;
        this.state.internalDocumentsOnly = !!res.data.internal_documents_only;
        this.state.selectedDocumentIds = res.data.document_ids || [];
        this.state.contextLabel = res.data.record_name || this.state.contextLabel;
        this.state.activeCitations = [];
        this.scrollToBottom();
    }

    formatMessage(content) {
        return safeMessageHtml(content);
    }

    onWorkspaceChange(ev) {
        this.state.workspaceId = parseInt(ev.target.value, 10);
        this.state.conversationId = false;
        this.state.messages = [];
        this.ensureConversation().then(() => this.refreshHistory());
    }

    onLanguageChange(ev) {
        this.state.language = ev.target.value;
    }

    onToggleInternal(ev) {
        this.state.internalDocumentsOnly = !!ev.target.checked;
    }

    onToggleWeb(ev) {
        this.state.allowWebResearch = !!ev.target.checked;
    }

    toggleDocument(id) {
        const set = new Set(this.state.selectedDocumentIds);
        if (set.has(id)) {
            set.delete(id);
        } else {
            set.add(id);
        }
        this.state.selectedDocumentIds = [...set];
    }

    async onNewConversation() {
        this.state.conversationId = false;
        this.state.messages = [];
        this.state.activeCitations = [];
        await this.ensureConversation();
        await this.refreshHistory();
    }

    async onSelectConversation(id) {
        await this.loadConversation(id);
    }

    async onSend() {
        const question = (this.state.question || "").trim();
        if (!question || this.state.loading) {
            return;
        }
        await this.ensureConversation();
        if (!this.state.conversationId) {
            return;
        }
        this.state.lastQuestion = question;
        this.state.question = "";
        this.state.loading = true;
        this.state.error = "";
        this.state.statusText = "Araştırılıyor…";
        this.state.messages.push({
            id: `tmp-u-${Date.now()}`,
            role: "user",
            content: question,
            status: "done",
            citation_count: 0,
            citations: [],
        });
        this.scrollToBottom();
        try {
            const res = await aiResearchService.postMessage(this.state.conversationId, {
                question,
                language: this.state.language,
                document_ids: this.state.selectedDocumentIds,
            });
            if (!res?.ok) {
                this.state.error = res?.error?.message || "Request failed.";
                return;
            }
            this.state.messages = res.data.conversation.messages || [];
            const assistant = res.data.assistant_message;
            if (assistant?.citations?.length) {
                this.state.activeCitations = assistant.citations;
            }
            await this.refreshHistory();
        } catch (e) {
            this.state.error = e.message || String(e);
        } finally {
            this.state.loading = false;
            this.state.statusText = "";
            this.scrollToBottom();
        }
    }

    async onStop() {
        if (!this.state.conversationId) {
            return;
        }
        await aiResearchService.stopGeneration(this.state.conversationId);
        this.state.loading = false;
        this.state.statusText = "";
    }

    async onRetryLast() {
        if (this.state.lastQuestion) {
            this.state.question = this.state.lastQuestion;
            await this.onSend();
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.onSend();
        }
    }

    async onCopy(msg) {
        try {
            await navigator.clipboard.writeText(msg.content || "");
            this.notification.add("Copied", { type: "success" });
        } catch (e) {
            this.notification.add("Copy failed", { type: "danger" });
        }
    }

    async onSaveNote(msg) {
        const res = await aiResearchService.saveNote(msg.id);
        if (res?.ok) {
            this.notification.add("CRM notu kaydedildi", { type: "success" });
        } else {
            this.notification.add(res?.error?.message || "Save failed", { type: "danger" });
        }
    }

    async onAttachResult(msg) {
        const res = await aiResearchService.attachResult(msg.id);
        if (res?.ok) {
            this.notification.add("Sonuç kayda eklendi", { type: "success" });
        } else {
            this.notification.add(res?.error?.message || "Attach failed", { type: "danger" });
        }
    }

    async onShowCitations(msg) {
        if (msg.citations?.length) {
            this.state.activeCitations = msg.citations;
            return;
        }
        const res = await aiResearchService.getCitations(msg.id);
        if (res?.ok) {
            this.state.activeCitations = res.data || [];
        }
    }

    onCitationClick(cite) {
        if (cite.source_url) {
            window.open(cite.source_url, "_blank", "noopener");
        }
    }

    async onFileSelected(ev) {
        const files = [...(ev.target.files || [])];
        if (!files.length || !this.state.workspaceId) {
            return;
        }
        this.state.statusText = "Belge yükleniyor…";
        for (const file of files) {
            const datas = await this.readFileAsBase64(file);
            const res = await aiResearchService.uploadDocument({
                workspace_id: this.state.workspaceId,
                name: file.name,
                datas,
                mimetype: file.type || "application/octet-stream",
                partner_id: this.state.crmContext.partner_id || undefined,
                lead_id: this.state.crmContext.lead_id || undefined,
                sync: true,
            });
            if (res?.ok) {
                const doc = res.data;
                if (!this.state.documents.find((d) => d.id === doc.id)) {
                    this.state.documents.push(doc);
                }
                if (!this.state.selectedDocumentIds.includes(doc.id)) {
                    this.state.selectedDocumentIds.push(doc.id);
                }
                if (doc.sync_state === "processing") {
                    this.state.statusText = "Belge İşleniyor";
                }
            } else {
                this.notification.add(res?.error?.message || "Upload failed", { type: "danger" });
            }
        }
        this.state.statusText = "";
        if (this.fileInput.el) {
            this.fileInput.el.value = "";
        }
    }

    readFileAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const result = reader.result || "";
                const base64 = String(result).split(",")[1] || "";
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    async onRetryDoc(documentId) {
        const res = await aiResearchService.syncDocument(documentId);
        if (res?.ok) {
            const idx = this.state.documents.findIndex((d) => d.id === documentId);
            if (idx >= 0) {
                this.state.documents[idx] = res.data;
            }
        } else {
            this.notification.add(res?.error?.message || "Sync failed", { type: "danger" });
        }
    }

    scrollToBottom() {
        requestAnimationFrame(() => {
            const el = this.messagesRef.el;
            if (el) {
                el.scrollTop = el.scrollHeight;
            }
        });
    }
}

registry.category("actions").add("tcrm_ai_research.assistant", ResearchAssistant);
