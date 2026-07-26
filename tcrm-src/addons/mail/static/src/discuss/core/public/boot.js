import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";

import { mount, whenReady } from "@tcrm/owl";

import { getTemplate } from "@web/core/templates";
import { appTranslateFn } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";

(async function boot() {
    await whenReady();

    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("DiscussClientAction", { Component: DiscussClientAction });

    const env = makeEnv();
    await startServices(env);
    env.services["mail.store"].insert(tcrm.discuss_data);
    tcrm.isReady = true;
    const root = await mount(MainComponentsContainer, document.body, {
        env,
        getTemplate,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
    });
    tcrm.__WOWL_DEBUG__ = { root };
})();
