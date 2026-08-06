// @tcrm-module ignore
// ! WARNING: this module must be loaded after `module_loader` but cannot have dependencies !

(function (tcrm) {
    "use strict";

    if (tcrm.define.name.endsWith("(hoot)")) {
        return;
    }

    const name = `${tcrm.define.name} (hoot)`;
    tcrm.define = {
        [name](name, dependencies, factory) {
            return tcrm.loader.define(name, dependencies, factory, !name.endsWith(".hoot"));
        },
    }[name];
})(globalThis.tcrm);
