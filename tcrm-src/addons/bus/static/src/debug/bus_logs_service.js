import { reactive } from "@tcrm/owl";

import { registry } from "@web/core/registry";

export const busLogsService = {
    dependencies: ["bus_service", "legacy_multi_tab", "worker_service"],
    /**
     * @param {import("@web/env").tcrmEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, { bus_service, legacy_multi_tab, worker_service }) {
        const state = reactive({
            enabled: legacy_multi_tab.getSharedValue("bus_log_menu.enabled", false),
            toggleLogging() {
                state.enabled = !state.enabled;
                if (bus_service.isActive) {
                    bus_service.setLoggingEnabled(state.enabled);
                }
                legacy_multi_tab.setSharedValue("bus_log_menu.enabled", state.enabled);
            },
        });
        legacy_multi_tab.bus.addEventListener("shared_value_updated", ({ detail }) => {
            if (detail.key === "bus_log_menu.enabled") {
                state.enabled = JSON.parse(detail.newValue);
            }
        });
        worker_service.connectionInitializedDeferred.then(() => {
            bus_service.setLoggingEnabled(state.enabled);
        });
        tcrm.busLogging = {
            stop: () => state.enabled && state.toggleLogging(),
            start: () => !state.enabled && state.toggleLogging(),
            download: () => bus_service.downloadLogs(),
        };
        if (state.enabled) {
            console.log(
                "Bus logging is enabled. To disable it, use `tcrm.busLogging.stop()`. To download the logs, use `tcrm.busLogging.download()`."
            );
        }
        return state;
    },
};

registry.category("services").add("bus.logs_service", busLogsService);
