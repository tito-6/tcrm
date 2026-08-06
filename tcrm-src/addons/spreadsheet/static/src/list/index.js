import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@tcrm/o-spreadsheet";

import "./list_functions";

import { ListCorePlugin } from "@spreadsheet/list/plugins/list_core_plugin";
import { ListCoreViewPlugin } from "@spreadsheet/list/plugins/list_core_view_plugin";
import { ListUIPlugin } from "@spreadsheet/list/plugins/list_ui_plugin";

import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "./list_actions";
const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

const { coreTypes, invalidateEvaluationCommands } = spreadsheet;

const { cellMenuRegistry } = spreadsheet.registries;

coreTypes.add("INSERT_tcrm_LIST");
coreTypes.add("RENAME_tcrm_LIST");
coreTypes.add("REMOVE_tcrm_LIST");
coreTypes.add("RE_INSERT_tcrm_LIST");
coreTypes.add("UPDATE_tcrm_LIST_DOMAIN");
coreTypes.add("UPDATE_tcrm_LIST");
coreTypes.add("ADD_LIST_DOMAIN");
coreTypes.add("DUPLICATE_tcrm_LIST");

invalidateEvaluationCommands.add("UPDATE_tcrm_LIST_DOMAIN");
invalidateEvaluationCommands.add("UPDATE_tcrm_LIST");
invalidateEvaluationCommands.add("INSERT_tcrm_LIST");
invalidateEvaluationCommands.add("REMOVE_tcrm_LIST");

cellMenuRegistry.add(
    "list_see_record",
    /** @type {import("@tcrm/o-spreadsheet").ActionSpec}*/ ({
        name: _t("See record"),
        sequence: 200,
        execute: async (env, isMiddleClick) => {
            const position = env.model.getters.getActivePosition();
            await SEE_RECORD_LIST(position, env, isMiddleClick);
        },
        isVisible: (env) => {
            const position = env.model.getters.getActivePosition();
            return SEE_RECORD_LIST_VISIBLE(position, env.model.getters);
        },
        icon: "o-spreadsheet-Icon.SEE_RECORDS",
    })
);

inverseCommandRegistry
    .add("INSERT_tcrm_LIST", identity)
    .add("UPDATE_tcrm_LIST_DOMAIN", identity)
    .add("UPDATE_tcrm_LIST", identity)
    .add("RE_INSERT_tcrm_LIST", identity)
    .add("RENAME_tcrm_LIST", identity)
    .add("REMOVE_tcrm_LIST", identity);

export { ListCorePlugin, ListCoreViewPlugin, ListUIPlugin };
