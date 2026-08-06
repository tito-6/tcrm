declare module "@spreadsheet" {
    import { CommandResult, CorePlugin, UIPlugin } from "@tcrm/o-spreadsheet";
    import { CommandResult as CR } from "@spreadsheet/o_spreadsheet/cancelled_reason";
    type tcrmCommandResult = CommandResult | typeof CR;

    export interface tcrmCorePlugin extends CorePlugin {
        getters: tcrmCoreGetters;
        dispatch: tcrmCoreDispatch;
        allowDispatch(command: AllCoreCommand): string | string[];
        beforeHandle(command: AllCoreCommand): void;
        handle(command: AllCoreCommand): void;
    }

    export interface tcrmCorePluginConstructor {
        new (config: unknown): tcrmCorePlugin;
    }

    export interface tcrmUIPlugin extends UIPlugin {
        getters: tcrmGetters;
        dispatch: tcrmDispatch;
        allowDispatch(command: AllCommand): string | string[];
        beforeHandle(command: AllCommand): void;
        handle(command: AllCommand): void;
    }

    export interface tcrmUIPluginConstructor {
        new (config: unknown): tcrmUIPlugin;
    }
}
