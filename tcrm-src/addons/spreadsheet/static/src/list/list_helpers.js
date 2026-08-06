// @ts-check

import { helpers } from "@tcrm/o-spreadsheet";

const { getFunctionsFromTokens } = helpers;

/** @typedef {import("@tcrm/o-spreadsheet").Token} Token */

/**
 * Parse a spreadsheet formula and detect the number of LIST functions that are
 * present in the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {number}
 */
export function getNumberOfListFormulas(tokens) {
    return getFunctionsFromTokens(tokens, ["TCRM.LIST", "TCRM.LIST.HEADER"]).length;
}

/**
 * Get the first List function description of the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {import("../helpers/tcrm_functions_helpers").tcrmFunctionDescription|undefined}
 */
export function getFirstListFunction(tokens) {
    return getFunctionsFromTokens(tokens, ["TCRM.LIST", "TCRM.LIST.HEADER"])[0];
}
