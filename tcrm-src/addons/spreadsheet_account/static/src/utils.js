// @ts-check

import { helpers } from "@tcrm/o-spreadsheet";

const { getFunctionsFromTokens } = helpers;

/**
 * @typedef {import("@tcrm/o-spreadsheet").Token} Token
 * @typedef  {import("@spreadsheet/helpers/tcrm_functions_helpers").tcrmFunctionDescription} tcrmFunctionDescription
 */

/**
 * @param {Token[]} tokens
 * @returns {number}
 */
export function getNumberOfAccountFormulas(tokens) {
    return getFunctionsFromTokens(tokens, ["TCRM.BALANCE", "TCRM.CREDIT", "TCRM.DEBIT", "TCRM.RESIDUAL", "TCRM.PARTNER.BALANCE", "TCRM.BALANCE.TAG"]).length;
}

/**
 * Get the first Account function description of the given formula.
 *
 * @param {Token[]} tokens
 * @returns {tcrmFunctionDescription | undefined}
 */
export function getFirstAccountFunction(tokens) {
    return getFunctionsFromTokens(tokens, ["TCRM.BALANCE", "TCRM.CREDIT", "TCRM.DEBIT", "TCRM.RESIDUAL", "TCRM.PARTNER.BALANCE", "TCRM.BALANCE.TAG"])[0];
}
