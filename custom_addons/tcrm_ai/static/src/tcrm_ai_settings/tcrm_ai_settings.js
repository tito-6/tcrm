/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useState } from "@tcrm/owl";

/**
 * Lightweight settings client action used by tours/tests.
 * Primary admin UI remains the form view under Ayarlar > TCRM AI.
 */
export class TcrmAiSettings extends Component {
    static template = "tcrm_ai.TcrmAiSettings";
    static props = { ...standardActionServiceProps };

    setup() {
        this.state = useState({
            status: null,
            apiKeyInput: "",
            model: "openai/gpt-oss-20b",
            provider: "groq",
            aiEnabled: false,
            saving: false,
            testing: false,
            message: "",
            error: "",
        });
        onWillStart(async () => {
            await this.reload();
        });
    }

    async reload() {
        const status = await rpc("/tcrm_ai/admin_status", {});
        this.state.status = status;
        this.state.model = status.model || "openai/gpt-oss-20b";
        this.state.provider = status.provider || "groq";
        this.state.aiEnabled = !!status.ai_enabled;
        this.state.apiKeyInput = "";
    }

    async onSave() {
        this.state.saving = true;
        this.state.error = "";
        this.state.message = "";
        try {
            const values = {
                provider: this.state.provider,
                model: this.state.model,
                ai_enabled: this.state.aiEnabled,
            };
            if (this.state.apiKeyInput) {
                values.api_key_input = this.state.apiKeyInput;
            }
            const status = await rpc("/tcrm_ai/settings/save", { values });
            this.state.status = status;
            this.state.apiKeyInput = "";
            this.state.message = _t("Ayarlar kaydedildi.");
        } catch (e) {
            this.state.error = e.message || String(e);
        } finally {
            this.state.saving = false;
        }
    }

    async onTest() {
        this.state.testing = true;
        this.state.error = "";
        this.state.message = "";
        try {
            const res = await rpc("/tcrm_ai/settings/test_connection", {});
            this.state.status = res.status || this.state.status;
            if (res.ok) {
                this.state.message = res.message || _t("Groq bağlantısı başarılı.");
            } else {
                this.state.error = res.message || _t("Bağlantı başarısız.");
            }
        } catch (e) {
            this.state.error = e.message || String(e);
        } finally {
            this.state.testing = false;
        }
    }
}

registry.category("actions").add("tcrm_ai.settings", TcrmAiSettings);
