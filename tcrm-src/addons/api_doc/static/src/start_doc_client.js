import { App, whenReady } from "@tcrm/owl";
import { getTemplate } from "@web/core/templates";
import { DocClient } from "@api_doc/doc_client";

export async function startDocClient() {
    await whenReady();
    const app = new App(DocClient, {
        getTemplate,
    });
    app.mount(document.body);
}

startDocClient();
