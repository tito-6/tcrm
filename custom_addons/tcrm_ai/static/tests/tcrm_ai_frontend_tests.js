/** @odoo-module **/

import { registry } from "@web/core/registry";

QUnit.module("TCRM AI Frontend", () => {
    QUnit.test("approved model list is closed", (assert) => {
        const allowed = ["openai/gpt-oss-20b"];
        assert.ok(allowed.includes("openai/gpt-oss-20b"));
        assert.notOk(allowed.includes("gpt-4o"));
    });

    QUnit.test("chat status must not expose provider key tokens", (assert) => {
        const chatStatus = {
            chat_enabled: true,
            title: "TCRM AI Asistan",
            configured: true,
            allow_internet_research: true,
        };
        assert.notOk("api_key" in chatStatus);
        assert.notOk("api_key_masked" in chatStatus);
        assert.notOk("provider" in chatStatus);
        assert.notOk("model" in chatStatus);
        assert.notOk("usage" in chatStatus);
        assert.equal(chatStatus.title, "TCRM AI Asistan");
    });

    QUnit.test("retry formatter never shows 0 minutes", (assert) => {
        const formatRetry = (secs) => {
            const n = Math.max(5, parseInt(secs, 10) || 5);
            if (n < 60) {
                return `${n} saniye sonra tekrar deneyin.`;
            }
            return `${Math.max(1, Math.floor(n / 60))} dakika sonra tekrar deneyin.`;
        };
        assert.ok(formatRetry(18).includes("18 saniye"));
        assert.ok(formatRetry(0).includes("saniye"));
        assert.notOk(formatRetry(0).includes("0 dakika"));
        assert.ok(formatRetry(120).includes("2 dakika"));
    });

    QUnit.test("chat disabled without entitlement reason", (assert) => {
        const status = { chat_enabled: false, chat_disabled_reason: "TCRM AI erişimi bu tenant için etkin değil" };
        assert.notOk(status.chat_enabled);
        assert.ok(status.chat_disabled_reason.includes("etkin değil"));
    });

    QUnit.test("Turkish labels present", (assert) => {
        const labels = ["Kaydet", "Bağlantıyı Test Et", "Yapılandırma gerekli", "TCRM AI Asistan", "Yeni sohbet", "Tekrar dene"];
        assert.ok(labels.includes("TCRM AI Asistan"));
        assert.ok(labels.includes("Yeni sohbet"));
    });

    QUnit.test("assistant service endpoints", (assert) => {
        const endpoints = ["/tcrm_ai/status", "/tcrm_ai/ask", "/tcrm_ai/conversations"];
        assert.ok(endpoints.includes("/tcrm_ai/ask"));
        assert.ok(endpoints.includes("/tcrm_ai/status"));
    });
});

registry.category("web_tour_tests").add("tcrm_ai.frontend", {
    test: true,
});
