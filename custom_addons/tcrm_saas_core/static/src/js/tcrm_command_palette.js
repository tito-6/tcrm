/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const tcrmCommandPaletteService = {
    dependencies: ["command", "action", "notification"],
    start(env, { command, action, notification }) {
        command.add(
            _t("TCRM: Natural Language Search & Action"),
            async () => {
                const query = window.prompt(
                    _t("Type your command (example: Show me all sales in Istanbul above 200000)")
                );
                if (!query) {
                    return;
                }
                try {
                    const result = await rpc("/tcrm_master/command_palette", { query });
                    if (result?.ok && result.action) {
                        await action.doAction(result.action);
                    } else {
                        notification.add(result?.message || _t("No matching command found."), {
                            title: _t("Command Palette"),
                            type: "warning",
                        });
                    }
                } catch (error) {
                    notification.add(
                        error?.message || _t("Failed to execute command."),
                        { title: _t("Command Palette"), type: "danger" }
                    );
                }
            },
            {
                global: true,
                category: "tcrm",
            }
        );
    },
};

registry.category("services").add("tcrm_command_palette", tcrmCommandPaletteService);
