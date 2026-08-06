import { SpreadsheetChildEnv as SSChildEnv } from "@tcrm/o-spreadsheet";
import { Services } from "services";

declare module "@spreadsheet" {
    import { Model } from "@tcrm/o-spreadsheet";

    export interface SpreadsheetChildEnv extends SSChildEnv {
        model: tcrmSpreadsheetModel;
        services: Services;
    }
}
