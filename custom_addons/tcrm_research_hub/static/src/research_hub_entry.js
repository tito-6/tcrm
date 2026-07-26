/** @odoo-module **/
/**
 * Registers the NotebookContainer Owl component as the client-action handler
 * for the "tcrm_master.research_hub" tag defined in research_hub_views.xml.
 *
 * The tag deliberately uses the "tcrm_master" namespace to stay visually
 * consistent with the rest of the TCRM Command Center action tags.
 */

import { registry } from "@web/core/registry";
import { NotebookContainer } from "./notebook_container";

registry
    .category("actions")
    .add("tcrm_master.research_hub", NotebookContainer, { force: true });
