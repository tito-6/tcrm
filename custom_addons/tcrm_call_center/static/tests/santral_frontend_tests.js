/** @odoo-module **/

import { getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { setupTestEnv } from "@web/../tests/helpers/mock_env";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { SantralDialer } from "@tcrm_call_center/dialer/dialer";
import { registry } from "@web/core/registry";
import { EventBus } from "@tcrm/owl";
import { callCenterService } from "@tcrm_call_center/services/call_center_service";

QUnit.module("Santral Dialer Frontend", (hooks) => {
    let target;

    hooks.beforeEach(async () => {
        target = getFixture();
        registry.category("services").add("notification", {
            start() {
                return { add: () => {} };
            },
        });
        registry.category("services").add("action", {
            start() {
                return { doAction: () => {} };
            },
        });
        
        // Mock Twilio window object
        window.Twilio = {
            Device: class MockDevice {
                constructor() {
                    this.registered = false;
                }
                on() {}
                async register() {
                    this.registered = true;
                }
                async connect() {
                    const call = {
                        handlers: {},
                        on(ev, cb) {
                            this.handlers[ev] = cb;
                        },
                        mute(state) {
                            this.muted = state;
                        },
                        disconnect() {
                            if (this.handlers["disconnect"]) {
                                this.handlers["disconnect"]();
                            }
                        }
                    };
                    return call;
                }
            }
        };
    });

    hooks.afterEach(() => {
        delete window.Twilio;
    });

    QUnit.test("double-click prevention and button states", async (assert) => {
        const mockRpc = async (route) => {
            if (route === "/tcrm/voice/token") {
                return { ok: true, data: { call_id: 123, dial_token: "abc", access_token: "def" } };
            }
            if (route === "/tcrm/voice/call/123/status") {
                return { ok: true, data: { status: "ringing" } };
            }
        };

        const env = await makeTestEnv({ mockRPC: mockRpc });
        env.services.call_center = registry.category("services").get("call_center").start(env, { notification: env.services.notification });

        const component = await mount(SantralDialer, target, {
            env,
            props: { action: { context: { phone_masked: "+90***" } } },
        });

        assert.strictEqual(target.querySelector("button.btn-primary").disabled, false, "Ara initially enabled");
        assert.strictEqual(target.querySelector("button.btn-danger").disabled, true, "Bitir initially disabled");

        // Click Ara
        await component.startCall();
        await nextTick();

        assert.strictEqual(target.querySelector("button.btn-primary").disabled, true, "Ara disabled while starting");
        
        const call = env.services.call_center.state;
        assert.strictEqual(call.callId, 123, "Call state saved immediately");

        // Force accept
        env.services.call_center.state.inCall = true;
        env.services.call_center.state.connecting = false;
        await nextTick();

        assert.strictEqual(target.querySelector("button.btn-danger").disabled, false, "Bitir enabled during call");
        
        // Disconnect
        await component.hangup();
        await nextTick();

        assert.strictEqual(target.querySelector("button.btn-danger").disabled, true, "Bitir disabled after disconnect");
    });

    QUnit.test("preflight connection test logic", async (assert) => {
        const mockRpc = async (route) => {
            if (route === "/tcrm/voice/token") {
                return { ok: true, data: { call_id: 123, dial_token: "abc", access_token: "def", edge: "frankfurt" } };
            }
        };

        const env = await makeTestEnv({ mockRPC: mockRpc });
        env.services.call_center = registry.category("services").get("call_center").start(env, { notification: env.services.notification });

        window.Twilio.Device.runPreflight = (token, options) => {
            assert.strictEqual(options.edge, "frankfurt");
            return {
                on: (ev, cb) => {
                    if (ev === "completed") {
                        cb({
                            edge: "frankfurt",
                            stats: {
                                rtt: { average: 150 },
                                jitter: { average: 10 },
                                packetLoss: { average: 0.5 },
                                mos: { average: 4.2 }
                            }
                        });
                    }
                }
            };
        };

        const component = await mount(SantralDialer, target, {
            env,
            props: { action: { context: { phone_masked: "+90***" } } },
        });
        
        await component.testConnection();
        await nextTick();
        
        const state = env.services.call_center.state;
        assert.strictEqual(state.preflightResult.grade, "Orta", "Grade is Orta based on rtt > 100");
        assert.strictEqual(state.preflightResult.rtt, 150);
        assert.strictEqual(state.diagnostics.selectedEdge, "roaming"); // will be updated inside ensureDevice later
    });
});
