declare module "@spreadsheet" {
    import { AddFunctionDescription, Arg, EvalContext } from "@tcrm/o-spreadsheet";

    export interface CustomFunctionDescription extends AddFunctionDescription {
        compute: (this: ExtendedEvalContext, ...args: Arg[]) => any;
    }

    interface ExtendedEvalContext extends EvalContext {
        getters: tcrmGetters;
    }
}
