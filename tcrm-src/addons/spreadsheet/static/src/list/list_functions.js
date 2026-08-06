import { _t } from "@web/core/l10n/translation";
import { helpers, registries, EvaluationError } from "@tcrm/o-spreadsheet";

const { arg, toString, toNumber } = helpers;
const { functionRegistry } = registries;

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

function assertListsExists(listId, getters) {
    if (!getters.isExistingList(listId)) {
        throw new EvaluationError(_t('There is no list with id "%s"', listId));
    }
}

const tcrm_LIST = {
    description: _t("Get the value from a list."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("index (string)", _t("Position of the record in the list.")),
        arg("field_name (string)", _t("Name of the field.")),
    ],
    category: "Tcrm",
    compute: function (listId, index, fieldName) {
        const id = toString(listId);
        const position = toNumber(index, this.locale) - 1;
        const _fieldName = toString(fieldName);
        if (!_fieldName) {
            return new EvaluationError(_t("The field name should not be empty."));
        }
        assertListsExists(id, this.getters);
        return this.getters.getListCellValueAndFormat(id, position, _fieldName);
    },
    returns: ["NUMBER", "STRING"],
};

const tcrm_LIST_HEADER = {
    description: _t("Get the header of a list."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("field_name (string)", _t("Technical field name.")),
        arg("field_display_name (string, optional)", _t("Name of the field.")),
    ],
    category: "Tcrm",
    compute: function (listId, fieldName, fieldDisplayName) {
        const id = toString(listId);
        const field = toString(fieldName);
        assertListsExists(id, this.getters);
        const displayName = toString(fieldDisplayName);
        const translatedDisplayName = this.getters.getListHeaderValue(id, field);
        return displayName || translatedDisplayName;
    },
    returns: ["NUMBER", "STRING"],
};

functionRegistry.add("TCRM.LIST", tcrm_LIST);
functionRegistry.add("TCRM.LIST.HEADER", tcrm_LIST_HEADER);
