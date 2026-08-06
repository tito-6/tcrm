import { tcrmPivotRuntimeDefinition } from "@spreadsheet/pivot/pivot_runtime";
import { ORM } from "@web/core/orm_service";
import { PivotMeasure } from "@spreadsheet/pivot/pivot_runtime";
import { ServerData } from "@spreadsheet/data_sources/server_data";
import { Pivot, CommonPivotCoreDefinition, PivotCoreDefinition } from "@tcrm/o-spreadsheet";

declare module "@spreadsheet" {
    export interface tcrmPivotCoreDefinition extends CommonPivotCoreDefinition {
        type: "tcrm";
        model: string;
        domain: Array;
        context: Object;
        actionXmlId: string;
    }

    export type ExtendedPivotCoreDefinition = PivotCoreDefinition | tcrmPivotCoreDefinition;

    interface tcrmPivot<T> extends Pivot<T> {
        type: ExtendedPivotCoreDefinition["type"];
    }
    export interface GFLocalPivot {
        id: string;
        fieldMatching: Record<string, any>;
    }

    export interface tcrmField {
        name: string;
        type: string;
        string: string;
        relation?: string;
        searchable?: boolean;
        aggregator?: string;
        store?: boolean;
    }

    export type tcrmFields = Record<string, Field | undefined>;

    export interface PivotMetaData {
        colGroupBys: string[];
        rowGroupBys: string[];
        activeMeasures: string[];
        resModel: string;
        fields?: Record<string, Field | undefined>;
        modelLabel?: string;
        fieldAttrs: any;
    }

    export interface PivotSearchParams {
        groupBy: string[];
        orderBy: string[];
        domain: Array;
        context: Object;
    }

    /* Params used for the tcrm pivot model */
    export interface WebPivotModelParams {
        metaData: PivotMetaData;
        searchParams: PivotSearchParams;
    }

    export interface tcrmPivotModelParams {
        fields: tcrmFields;
        definition: tcrmPivotRuntimeDefinition;
        searchParams: {
            domain: Array;
            context: Object;
        };
    }

    export interface PivotModelServices {
        serverData: ServerData;
        orm: ORM;
        getters: tcrmGetters;
    }
}
