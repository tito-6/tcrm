// @tcrm-module ignore

//-----------------------------------------------------------------------------
// Tcrm Web Boostrap Code
//-----------------------------------------------------------------------------

(function (tcrm) {
    "use strict";

    if (tcrm.loader) {
        // Allows for duplicate calls to `module_loader`: only the first one is
        // executed.
        return;
    }

    class ModuleLoader {
        /** @type {tcrmModuleLoader["bus"]} */
        bus = new EventTarget();
        /** @type {tcrmModuleLoader["checkErrorProm"]} */
        checkErrorProm = null;
        /** @type {tcrmModuleLoader["factories"]} */
        factories = new Map();
        /** @type {tcrmModuleLoader["failed"]} */
        failed = new Set();
        /** @type {tcrmModuleLoader["jobs"]} */
        jobs = new Set();
        /** @type {tcrmModuleLoader["modules"]} */
        modules = new Map();

        /**
         * @param {HTMLElement} [root]
         */
        constructor(root) {
            this.root = root;

            const strDebug = new URLSearchParams(location.search).get("debug");
            this.debug = Boolean(strDebug && strDebug !== "0");
        }

        /** @type {tcrmModuleLoader["addJob"]} */
        addJob(name) {
            this.jobs.add(name);
            this.startModules();
        }

        /** @type {tcrmModuleLoader["define"]} */
        define(name, deps, factory, lazy = false) {
            if (typeof name !== "string") {
                throw new Error(`Module name should be a string, got: ${String(name)}`);
            }
            if (!Array.isArray(deps)) {
                throw new Error(
                    `Module dependencies should be a list of strings, got: ${String(deps)}`
                );
            }
            if (typeof factory !== "function") {
                throw new Error(`Module factory should be a function, got: ${String(factory)}`);
            }
            if (this.factories.has(name)) {
                return; // Ignore duplicate modules
            }
            this.factories.set(name, {
                deps,
                fn: factory,
                ignoreMissingDeps: globalThis.__tcrmIgnoreMissingDependencies,
            });
            if (!lazy) {
                this.addJob(name);
                this.checkErrorProm ||= Promise.resolve().then(() => {
                    this.checkErrorProm = null;
                    this.reportErrors(this.findErrors());
                });
            }
        }

        /** @type {tcrmModuleLoader["findErrors"]} */
        findErrors(moduleNames) {
            /**
             * @param {Iterable<string>} currentModuleNames
             * @param {Set<string>} visited
             * @returns {string | null}
             */
            const findCycle = (currentModuleNames, visited) => {
                for (const name of currentModuleNames || []) {
                    if (visited.has(name)) {
                        const cycleModuleNames = [...visited, name];
                        return cycleModuleNames
                            .slice(cycleModuleNames.indexOf(name))
                            .map((j) => `"${j}"`)
                            .join(" => ");
                    }
                    const cycle = findCycle(dependencyGraph[name], new Set(visited).add(name));
                    if (cycle) {
                        return cycle;
                    }
                }
                return null;
            };

            moduleNames ||= this.jobs;

            /** @type {Record<string, Iterable<string>>} */
            const dependencyGraph = Object.create(null);
            /** @type {Set<string>} */
            const missing = new Set();
            /** @type {Set<string>} */
            const unloaded = new Set();

            for (const moduleName of moduleNames) {
                const { deps, ignoreMissingDeps } = this.factories.get(moduleName);

                dependencyGraph[moduleName] = deps;

                if (ignoreMissingDeps) {
                    continue;
                }

                unloaded.add(moduleName);
                for (const dep of deps) {
                    if (!this.factories.has(dep)) {
                        missing.add(dep);
                    }
                }
            }

            const cycle = findCycle(moduleNames, new Set());
            const errors = {};
            if (cycle) {
                errors.cycle = cycle;
            }
            if (this.failed.size) {
                errors.failed = this.failed;
            }
            if (missing.size) {
                errors.missing = missing;
            }
            if (unloaded.size) {
                errors.unloaded = unloaded;
            }
            return errors;
        }

        /** @type {tcrmModuleLoader["findJob"]} */
        findJob() {
            for (const job of this.jobs) {
                if (this.factories.get(job).deps.every((dep) => this.modules.has(dep))) {
                    return job;
                }
            }
            return null;
        }

        /** @type {tcrmModuleLoader["reportErrors"]} */
        async reportErrors(errors) {
            if (!Object.keys(errors).length) {
                return;
            }

            if (errors.failed) {
                console.error("The following modules failed to load because of an error:", [
                    ...errors.failed,
                ]);
            }
            if (errors.missing) {
                console.error(
                    "The following modules are needed by other modules but have not been defined, they may not be present in the correct asset bundle:",
                    [...errors.missing]
                );
            }
            if (errors.cycle) {
                console.error(
                    "The following modules could not be loaded because they form a dependency cycle:",
                    errors.cycle
                );
            }
            if (errors.unloaded) {
                console.error(
                    "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:",
                    [...errors.unloaded]
                );
            }

            const document = this.root?.ownerDocument || globalThis.document;
            if (document.readyState === "loading") {
                await new Promise((resolve) =>
                    document.addEventListener("DOMContentLoaded", resolve)
                );
            }

            if (this.debug) {
                const style = document.createElement("style");
                style.className = "o_module_error_banner";
                style.textContent = `
                    body::before {
                        font-weight: bold;
                        content: "An error occurred while loading javascript modules, you may find more information in the devtools console";
                        position: fixed;
                        left: 0;
                        bottom: 0;
                        z-index: 100000000000;
                        background-color: #C00;
                        color: #DDD;
                    }
                `;
                document.head.appendChild(style);
            }
        }

        /** @type {tcrmModuleLoader["startModules"]} */
        startModules() {
            let job;
            while ((job = this.findJob())) {
                this.startModule(job);
            }
        }

        /** @type {tcrmModuleLoader["startModule"]} */
        startModule(name) {
            /** @type {(dependency: string) => tcrmModule} */
            const require = (dependency) => this.modules.get(dependency);
            this.jobs.delete(name);
            const factory = this.factories.get(name);
            /** @type {tcrmModule | null} */
            let module = null;
            try {
                module = factory.fn(require);
            } catch (error) {
                this.failed.add(name);
                throw new Error(`Error while loading "${name}":\n${error}`);
            }
            this.modules.set(name, module);
            this.bus.dispatchEvent(
                new CustomEvent("module-started", {
                    detail: { moduleName: name, module },
                })
            );
            return module;
        }
    }

    const loader = new ModuleLoader();
    tcrm.define = loader.define.bind(loader);
    tcrm.loader = loader;

    if (tcrm.debug && !loader.debug) {
        // remove debug mode if not explicitely set in url
        tcrm.debug = "";
    }
})((globalThis.tcrm ||= {}));
