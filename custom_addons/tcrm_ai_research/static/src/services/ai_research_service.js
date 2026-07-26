/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

/**
 * Thin client for authenticated TCRM AI Research JSON-RPC routes.
 * Never receives or stores RAGFlow credentials.
 */
export const aiResearchService = {
    async getConfig() {
        return rpc("/tcrm_ai/config", {});
    },
    async listWorkspaces() {
        return rpc("/tcrm_ai/workspaces", {});
    },
    async listConversations(params = {}) {
        return rpc("/tcrm_ai/conversations/list", params);
    },
    async createConversation(params) {
        return rpc("/tcrm_ai/conversations", { ...params, create: true });
    },
    async getConversation(conversationId) {
        return rpc(`/tcrm_ai/conversations/${conversationId}`, {});
    },
    async postMessage(conversationId, params) {
        return rpc(`/tcrm_ai/conversations/${conversationId}/message`, params);
    },
    async stopGeneration(conversationId) {
        return rpc(`/tcrm_ai/conversations/${conversationId}/stop`, {});
    },
    async listDocuments(workspaceId) {
        return rpc("/tcrm_ai/documents", { workspace_id: workspaceId });
    },
    async uploadDocument(params) {
        return rpc("/tcrm_ai/documents/upload", params);
    },
    async syncDocument(documentId) {
        return rpc(`/tcrm_ai/documents/${documentId}/sync`, {});
    },
    async getCitations(messageId) {
        return rpc(`/tcrm_ai/messages/${messageId}/citations`, {});
    },
    async saveNote(messageId) {
        return rpc(`/tcrm_ai/messages/${messageId}/save-note`, {});
    },
    async attachResult(messageId) {
        return rpc(`/tcrm_ai/messages/${messageId}/attach-result`, {});
    },
    async previewContext(params) {
        return rpc("/tcrm_ai/context/preview", params);
    },
};
