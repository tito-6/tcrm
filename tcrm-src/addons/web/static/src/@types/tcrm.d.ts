interface tcrmModuleErrors {
    cycle?: string | null;
    failed?: Set<string>;
    missing?: Set<string>;
    unloaded?: Set<string>;
}

interface tcrmModuleFactory {
    deps: string[];
    fn: tcrmModuleFactoryFn;
    ignoreMissingDeps: boolean;
}

class tcrmModuleLoader {
    bus: EventTarget;
    checkErrorProm: Promise<void> | null;
    debug: boolean;
    /**
     * Mapping [name => factory]
     */
    factories: Map<string, tcrmModuleFactory>;
    /**
     * Names of failed modules
     */
    failed: Set<string>;
    /**
     * Names of modules waiting to be started
     */
    jobs: Set<string>;
    /**
     * Mapping [name => module]
     */
    modules: Map<string, tcrmModule>;

    constructor(root?: HTMLElement);

    addJob: (name: string) => void;

    define: (
        name: string,
        deps: string[],
        factory: tcrmModuleFactoryFn,
        lazy?: boolean
    ) => tcrmModule;

    findErrors: (jobs?: Iterable<string>) => tcrmModuleErrors;

    findJob: () => string | null;

    reportErrors: (errors: tcrmModuleErrors) => Promise<void>;

    sortFactories: () => void;

    startModule: (name: string) => tcrmModule;

    startModules: () => void;
}

type tcrmModule = Record<string, any>;

type tcrmModuleFactoryFn = (require: (dependency: string) => tcrmModule) => tcrmModule;

declare const tcrm: {
    csrf_token: string;
    debug: string;
    define: tcrmModuleLoader["define"];
    loader: tcrmModuleLoader;
};
