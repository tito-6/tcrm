/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@tcrm/owl";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { useService } from "@web/core/utils/hooks";

export class SantralDialer extends Component {
    static template = "tcrm_call_center.Dialer";
    static props = { ...standardActionServiceProps };

    setup() {
        this.notification = useService("notification");
        this.callCenter = useService("call_center");
        this.state = useState(this.callCenter.state);

        // Component local UI state
        this.localState = useState({
            notes: "",
            outcome: "",
            createFollowup: false,
        });
        this.ui = useState({
            proximityNear: false,
            showDevices: false,
            showKeypad: false,
            speakerOn: false,
        });

        const ctx = this.props.action?.context || {};
        if (!this.state.callId && !this.state.inCall && !this.state.connecting) {
            this.state.callId = ctx.call_id || false;
            this.state.leadId = ctx.lead_id || false;
            this.state.partnerId = ctx.partner_id || false;
            this.state.recordName = ctx.record_name || "";
            this.state.phoneMasked = ctx.phone_masked || "";
            this.state.projectName = ctx.project_name || "";
        }

        this._wakeLock = null;
        this._proximitySensor = null;
        this._onDeviceProximity = null;
        this._onUserProximity = null;
        this._onVisibility = null;

        onMounted(() => {
            this.bootstrap();
            this.setupProximity();
            this.acquireWakeLock();
        });
        onWillUnmount(() => this.teardownProximity());
    }

    get initials() {
        const n = (this.state.recordName || "").trim();
        if (!n) return "☎";
        const parts = n.split(/\s+/).filter(Boolean);
        const first = parts[0]?.[0] || "";
        const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
        return (first + last).toUpperCase() || "☎";
    }

    async bootstrap() {
        if (!window.isSecureContext && location.hostname !== "localhost") {
            this.state.error = "Tarayıcı araması için HTTPS gerekli.";
            return;
        }
        await this.callCenter.checkMic();
    }

    // ---- Proximity ("ear") sensor + wake lock (mobile) ----
    setupProximity() {
        const setNear = (near) => { this.ui.proximityNear = !!near; };

        // 1) Modern Generic Sensor API (Chrome Android w/ flag / some devices)
        if (typeof window.ProximitySensor === "function") {
            try {
                const sensor = new window.ProximitySensor({ frequency: 10 });
                sensor.addEventListener("reading", () => {
                    // `near` is boolean; `distance` in cm when available
                    const near = sensor.near === true ||
                        (typeof sensor.distance === "number" && sensor.distance >= 0 && sensor.distance < 5);
                    setNear(near);
                });
                sensor.addEventListener("error", () => {});
                sensor.start();
                this._proximitySensor = sensor;
            } catch (_) { /* permission / not available */ }
        }

        // 2) Legacy DeviceProximityEvent (older Firefox mobile)
        if ("ondeviceproximity" in window) {
            this._onDeviceProximity = (e) => {
                const max = e.max || 10;
                setNear(e.near === true || (typeof e.value === "number" && e.value < max / 2));
            };
            window.addEventListener("deviceproximity", this._onDeviceProximity);
        }
        // 3) Legacy UserProximityEvent
        if ("onuserproximity" in window) {
            this._onUserProximity = (e) => setNear(e.near === true);
            window.addEventListener("userproximity", this._onUserProximity);
        }
    }

    async acquireWakeLock() {
        try {
            if ("wakeLock" in navigator && navigator.wakeLock.request) {
                this._wakeLock = await navigator.wakeLock.request("screen");
                // Re-acquire on visibility change (browsers auto-release when hidden)
                this._onVisibility = async () => {
                    if (document.visibilityState === "visible" && !this._wakeLock) {
                        try { this._wakeLock = await navigator.wakeLock.request("screen"); } catch (_) {}
                    }
                };
                document.addEventListener("visibilitychange", this._onVisibility);
            }
        } catch (_) { /* wake lock not available */ }
    }

    teardownProximity() {
        try { this._proximitySensor?.stop?.(); } catch (_) {}
        if (this._onDeviceProximity) window.removeEventListener("deviceproximity", this._onDeviceProximity);
        if (this._onUserProximity) window.removeEventListener("userproximity", this._onUserProximity);
        if (this._onVisibility) document.removeEventListener("visibilitychange", this._onVisibility);
        try { this._wakeLock?.release?.(); } catch (_) {}
        this._wakeLock = null;
    }

    // ---- Call actions ----
    async startCall() {
        const payload = {};
        if (this.state.callId) payload.call_id = this.state.callId;
        else if (this.state.leadId) { payload.res_model = "crm.lead"; payload.res_id = this.state.leadId; }
        else if (this.state.partnerId) { payload.res_model = "res.partner"; payload.res_id = this.state.partnerId; }
        await this.callCenter.startCall(payload);
    }

    async testConnection() {
        const payload = {};
        if (this.state.callId) payload.call_id = this.state.callId;
        else if (this.state.leadId) { payload.res_model = "crm.lead"; payload.res_id = this.state.leadId; }
        else if (this.state.partnerId) { payload.res_model = "res.partner"; payload.res_id = this.state.partnerId; }
        await this.callCenter.runPreflight(payload);
    }

    onMicrophoneChange(ev) { this.callCenter.selectMicrophone(ev.target.value); }
    onSpeakerChange(ev) { this.callCenter.selectSpeaker(ev.target.value); }

    toggleMute() { this.callCenter.toggleMute(); }
    hangup() { this.callCenter.hangup(); }

    toggleDevices() { this.ui.showDevices = !this.ui.showDevices; }
    toggleKeypad() { this.ui.showKeypad = !this.ui.showKeypad; }

    toggleSpeaker() {
        this.ui.speakerOn = !this.ui.speakerOn;
        if (this.callCenter.setSpeakerphone) {
            this.callCenter.setSpeakerphone(this.ui.speakerOn);
        }
    }

    sendDigit(digit) {
        if (this.callCenter.sendDigits) {
            this.callCenter.sendDigits(digit);
        }
    }

    async saveWrapup() {
        if (!this.state.callId) {
            this.notification.add("Önce arama başlatın.", { type: "warning" });
            return;
        }
        try {
            const res = await this.callCenter.wrapup({
                outcome: this.localState.outcome || false,
                notes: this.localState.notes,
                create_followup: this.localState.createFollowup,
                followup_summary: this.localState.outcome ? `Santral: ${this.localState.outcome}` : "Santral takip",
            });
            if (!res?.ok) {
                throw new Error(res?.error?.message || "Kayıt başarısız");
            }
            this.notification.add("Çağrı sonucu kaydedildi.", { type: "success" });
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
    }
}

registry.category("actions").add("tcrm_call_center.dialer", SantralDialer);
