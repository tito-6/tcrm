declare module "@spreadsheet" {
    import { Model } from "@tcrm/o-spreadsheet";

    export interface tcrmSpreadsheetModel extends Model {
        getters: tcrmGetters;
        dispatch: tcrmDispatch;
    }

    export interface tcrmSpreadsheetModelConstructor {
        new (
            data: object,
            config: Partial<Model["config"]>,
            revisions: object[]
        ): tcrmSpreadsheetModel;
    }
}
