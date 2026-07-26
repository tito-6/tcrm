import { rpc } from "@web/core/network/rpc";
import { reactive } from "@tcrm/owl";
import { registry } from "@web/core/registry";
import { EventBus } from "@tcrm/owl";

export const STATUS_TR = {
    idle: "Hazır",
    connecting: "Bağlanıyor",
    ringing: "Çalıyor",
    "in-progress": "Görüşme devam ediyor",
    answered: "Görüşme devam ediyor",
    completed: "Tamamlandı",
    busy: "Meşgul",
    failed: "Başarısız",
    "no-answer": "Cevapsız",
    canceled: "İptal edildi",
    pending: "Bekliyor",
    reconnecting: "Yeniden bağlanıyor",
};

export function formatTimer(seconds) {
    const s = Math.max(0, seconds | 0);
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    return `${mm}:${ss}`;
}

const callCenterServiceFactory = {
    dependencies: ["notification"],
    start(env, { notification }) {
        const state = reactive({
            callId: false,
            dialToken: "",
            leadId: false,
            partnerId: false,
            recordName: "",
            phoneMasked: "",
            projectName: "",
            callStatus: "idle",
            callStatusLabel: STATUS_TR.idle,
            micLabel: "Bilinmiyor",
            timerLabel: "00:00",
            recordingLabel: "",
            recordingId: false,
            muted: false,
            inCall: false,
            connecting: false,
            busy: false,
            notConfigured: false,
            error: "",
            elapsed: 0,
            
            // Diagnostics & Devices
            microphones: [],
            speakers: [],
            selectedMicrophone: localStorage.getItem("santral_mic_id") || "default",
            selectedSpeaker: localStorage.getItem("santral_speaker_id") || "default",
            
            diagnostics: {
                sdkVersion: "2.18.3",
                browserOS: navigator.userAgent,
                selectedEdge: "roaming",
                codec: "",
                rtt: null,
                jitter: null,
                packetLoss: null,
                mos: null,
                warningEvents: "",
                connectionType: "UDP",
                microphoneDevice: ""
            },
            
            preflightRunning: false,
            preflightResult: null,
            preflightWarning: "",
            liveWarning: "",
            
            tokenData: null,
        });

        let device = null;
        let activeCall = null;
        let timer = null;
        let pollTimer = null;
        let starting = false;

        const bus = new EventBus();

        function setStatus(status) {
            state.callStatus = status;
            state.callStatusLabel = STATUS_TR[status] || status;
        }

        function startTimer() {
            if (timer) clearInterval(timer);
            state.elapsed = 0;
            state.timerLabel = formatTimer(0);
            timer = setInterval(() => {
                state.elapsed += 1;
                state.timerLabel = formatTimer(state.elapsed);
            }, 1000);
        }

        function stopTimer() {
            if (timer) clearInterval(timer);
            timer = null;
        }

        function startPolling() {
            if (pollTimer) clearInterval(pollTimer);
            pollTimer = setInterval(async () => {
                if (!state.callId) return;
                try {
                    const res = await rpc(`/tcrm/voice/call/${state.callId}/status`, {});
                    if (!res?.ok) return;
                    const data = res.data || {};
                    if (data.status && !state.inCall) {
                        setStatus(data.status);
                    }
                    if (data.recording_state === "ready") {
                        state.recordingLabel = "Hazır";
                    } else if (data.recording_state === "pending") {
                        state.recordingLabel = "Hazırlanıyor";
                    } else if (data.recording_state) {
                        state.recordingLabel = data.recording_state;
                    }
                    if (data.recording_id) {
                        state.recordingId = data.recording_id;
                    }
                    if (data.user_error_message && !state.error) {
                        state.error = data.user_error_message;
                    }
                } catch (_) {
                    /* ignore */
                }
            }, 2500);
        }

        function stopPolling() {
            if (pollTimer) clearInterval(pollTimer);
            pollTimer = null;
        }

        async function ensureTwilioSDK() {
            if (window.Twilio?.Device) return;
            return new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.src = "/tcrm_call_center/static/src/lib/twilio.min.js";
                script.onload = () => resolve();
                script.onerror = () => reject(new Error("Twilio script tag failed to load."));
                document.head.appendChild(script);
            });
        }

        async function refreshDevices() {
            try {
                // Ensure permissions
                await navigator.mediaDevices.getUserMedia({ audio: true });
                const devs = await navigator.mediaDevices.enumerateDevices();
                state.microphones = devs.filter(d => d.kind === "audioinput").map(d => ({ id: d.deviceId, label: d.label || "Mikrofon" }));
                state.speakers = devs.filter(d => d.kind === "audiooutput").map(d => ({ id: d.deviceId, label: d.label || "Hoparlör" }));
                
                if (state.microphones.length > 0) {
                    const mic = state.microphones.find(m => m.id === state.selectedMicrophone) || state.microphones[0];
                    state.diagnostics.microphoneDevice = mic.label;
                }
            } catch (e) {
                state.error = "Ses cihazlarına erişilemedi.";
            }
        }
        
        async function setAudioDevices() {
            if (!device) return;
            try {
                if (state.selectedMicrophone) {
                    await device.audio.setInputDevice(state.selectedMicrophone);
                }
                if (state.selectedSpeaker && device.audio.speakerDevices) {
                    device.audio.speakerDevices.set(state.selectedSpeaker);
                }
            } catch (e) {
                console.warn("Failed to set audio device", e);
            }
        }

        async function ensureDevice(tokenData) {
            try {
                await ensureTwilioSDK();
            } catch (e) {
                throw new Error("Twilio Voice SDK yüklenemedi: " + e.message);
            }
            if (!window.Twilio?.Device) {
                throw new Error("Twilio Voice SDK yüklenemedi (window.Twilio missing).");
            }
            
            const accessToken = tokenData.access_token;
            const rtcConfiguration = tokenData.ice_servers?.length > 0 ? { iceServers: tokenData.ice_servers } : undefined;
            
            if (!device) {
                device = new window.Twilio.Device(accessToken, {
                    codecPreferences: ["opus", "pcmu"],
                    edge: tokenData.edge || "roaming",
                    dscp: true,
                    maxCallSignalingTimeoutMs: 30000,
                    enableImprovedSignalingErrorPrecision: true,
                    closeProtection: "Aktif görüşme var. Sayfadan ayrılmak görüşmeyi sonlandırır.",
                    appName: "TCRM Santral",
                    appVersion: "1.0",
                    rtcConfiguration: rtcConfiguration,
                });
                
                device.on("error", (err) => {
                    const msg = err?.message || String(err);
                    if (/token/i.test(msg)) {
                        state.error = "Oturum süresi doldu. Yeniden arayın.";
                    } else {
                        state.error = msg;
                    }
                    state.connecting = false;
                    state.inCall = false;
                    setStatus("failed");
                });
                await device.register();
                await setAudioDevices();
            } else {
                device.updateToken(accessToken);
            }
            
            state.diagnostics.selectedEdge = tokenData.edge || "roaming";
            return device;
        }
        
        async function runPreflight(payload) {
            if (state.preflightRunning) return;
            state.preflightRunning = true;
            state.preflightResult = null;
            state.preflightWarning = "";
            state.error = "";
            
            try {
                await refreshDevices();
                
                // Need token to run preflight
                if (!state.tokenData) {
                    const res = await rpc("/tcrm/voice/token", payload);
                    if (!res?.ok) throw new Error(res?.error?.message || "Token alınamadı");
                    state.tokenData = res.data;
                }
                
                await ensureTwilioSDK();
                
                const rtcConfiguration = state.tokenData.ice_servers?.length > 0 ? { iceServers: state.tokenData.ice_servers } : undefined;
                
                const edgesToTest = ["roaming", "frankfurt", "dublin"];
                let bestEdge = null;
                let bestStats = null;
                
                // Fallback testing logic - we test the configured edge first. If poor, we test fallback.
                const edgeToTest = state.tokenData.edge || "roaming";
                
                const preflight = window.Twilio.Device.runPreflight(state.tokenData.access_token, {
                    edge: edgeToTest,
                    codecPreferences: ["opus", "pcmu"],
                    rtcConfiguration: rtcConfiguration
                });
                
                preflight.on('completed', (report) => {
                    const stats = report.stats;
                    const rtt = report.stats?.rtt?.average || 0;
                    const jitter = report.stats?.jitter?.average || 0;
                    const loss = report.stats?.packetLoss?.average || 0;
                    const mos = report.stats?.mos?.average || 0;
                    
                    let grade = "İyi";
                    if (rtt > 200 || jitter > 30 || loss > 3) {
                        grade = "Zayıf";
                        state.preflightWarning = "Gecikme, Jitter veya Paket Kaybı çok yüksek. Çağrı kalitesi kötü olabilir.";
                    } else if (rtt > 100 || jitter > 15 || loss > 1) {
                        grade = "Orta";
                    }
                    
                    state.preflightResult = {
                        edge: report.edge,
                        rtt: Math.round(rtt),
                        jitter: Math.round(jitter),
                        loss: loss.toFixed(2),
                        mos: mos.toFixed(2),
                        grade: grade
                    };
                    
                    // Save to diagnostics
                    state.diagnostics.rtt = Math.round(rtt);
                    state.diagnostics.jitter = Math.round(jitter);
                    state.diagnostics.packetLoss = parseFloat(loss.toFixed(2));
                    state.diagnostics.mos = parseFloat(mos.toFixed(2));
                    
                    state.preflightRunning = false;
                });
                
                preflight.on('failed', (error) => {
                    state.error = "Preflight Testi başarısız: " + error.message;
                    state.preflightRunning = false;
                });
                
            } catch (e) {
                state.error = e.message || "Bağlantı testi başarısız oldu.";
                state.preflightRunning = false;
            }
        }

        async function startCall(payload) {
            if (starting || state.inCall || state.connecting) {
                return false;
            }
            starting = true;
            state.busy = true;
            state.error = "";
            state.connecting = true;
            state.muted = false;
            state.recordingLabel = "Kayıt hazırlanıyor";
            state.liveWarning = "";
            state.diagnostics.warningEvents = "";
            setStatus("connecting");
            
            await refreshDevices();

            try {
                let tokenData = state.tokenData;
                if (!tokenData) {
                    const res = await rpc("/tcrm/voice/token", payload);
                    if (!res?.ok) {
                        const code = res?.error?.code;
                        const msg = res?.error?.message || "Token alınamadı";
                        if (code === "not_configured" || /yapılandırılmamış/i.test(msg)) {
                            state.notConfigured = true;
                        }
                        throw new Error(msg);
                    }
                    tokenData = res.data;
                    state.tokenData = tokenData;
                }
                
                state.callId = tokenData.call_id;
                state.dialToken = tokenData.dial_token;
                if (tokenData.destination_masked) state.phoneMasked = tokenData.destination_masked;
                if (tokenData.record_name) state.recordName = tokenData.record_name;
                if (tokenData.project_name) state.projectName = tokenData.project_name;
                
                startPolling();

                await ensureDevice(tokenData);
                
                const params = {
                    callId: String(tokenData.call_id),
                    dialToken: tokenData.dial_token,
                };
                
                const callOptions = {
                    audioConstraints: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        channelCount: 1,
                    }
                };
                
                activeCall = await device.connect({ params }, callOptions);
                
                // Track Warnings
                activeCall.on('warning', (name) => {
                    const warnMsgMap = {
                        'high-rtt': 'Yüksek gecikme',
                        'high-jitter': 'Ses kesintili olabilir (Jitter)',
                        'high-packet-loss': 'Paket kaybı algılandı',
                        'low-mos': 'İnternet bağlantısı zayıf',
                        'audio-input-level': 'Mikrofon sesi algılanmıyor'
                    };
                    const msg = warnMsgMap[name] || `Uyarı: ${name}`;
                    state.liveWarning = msg;
                    state.diagnostics.warningEvents += `${new Date().toISOString()} WARN: ${name}\n`;
                });
                
                activeCall.on('warning-cleared', (name) => {
                    state.liveWarning = "Bağlantı düzeldi";
                    setTimeout(() => { if (state.liveWarning === "Bağlantı düzeldi") state.liveWarning = ""; }, 3000);
                    state.diagnostics.warningEvents += `${new Date().toISOString()} CLEAR: ${name}\n`;
                });
                
                // Media info for diagnostics
                activeCall.on('sample', (sample) => {
                    if (!state.diagnostics.codec && sample.codecName) {
                        state.diagnostics.codec = sample.codecName;
                    }
                });

                activeCall.on("ringing", () => setStatus("ringing"));
                activeCall.on("accept", () => {
                    state.inCall = true;
                    state.connecting = false;
                    setStatus("in-progress");
                    if (tokenData.recording_enabled) {
                        state.recordingLabel = "Kayıt devam ediyor";
                    }
                    startTimer();
                    
                    // Final media info
                    const pc = activeCall.mediaStream?.peerConnection;
                    if (pc && pc.connectionState) {
                        state.diagnostics.connectionType = "WebRTC (" + pc.connectionState + ")";
                    }
                });
                activeCall.on("disconnect", () => {
                    state.inCall = false;
                    state.connecting = false;
                    stopTimer();
                    if (state.callStatus === "in-progress" || state.callStatus === "ringing") {
                        setStatus("completed");
                    }
                    if (tokenData.recording_enabled) {
                        state.recordingLabel = "Kayıt işleniyor";
                    }
                    state.tokenData = null; // Clear token for next call
                });
                activeCall.on("cancel", () => {
                    state.inCall = false;
                    state.connecting = false;
                    stopTimer();
                    setStatus("canceled");
                    state.tokenData = null;
                });
                activeCall.on("reject", () => {
                    state.inCall = false;
                    state.connecting = false;
                    stopTimer();
                    setStatus("busy");
                    state.tokenData = null;
                });
                activeCall.on("error", async (error) => {
                    if (error.code === 31005) {
                        // 31005: Normal hangup mapping logic
                        state.inCall = false;
                        state.connecting = false;
                        stopTimer();
                        try {
                            const statusRes = await rpc(`/tcrm/voice/call/${state.callId}/status`, {});
                            if (statusRes?.ok && statusRes.data) {
                                const st = statusRes.data.status;
                                if (st === 'no-answer' || st === 'busy' || st === 'completed') {
                                    setStatus(st);
                                    if (st === 'no-answer') state.recordingLabel = "Kayıt oluşturulmadı";
                                    state.tokenData = null;
                                    return;
                                }
                                if (st === 'failed') {
                                    setStatus('failed');
                                    state.error = statusRes.data.user_error_message || "Arama başarısız.";
                                    state.tokenData = null;
                                    return;
                                }
                            }
                        } catch(e) {}
                        setStatus("completed");
                    } else {
                        state.error = error.message;
                        setStatus("failed");
                        state.inCall = false;
                        state.connecting = false;
                        stopTimer();
                    }
                    state.tokenData = null;
                });
                
                setStatus("ringing");
                return true;
            } catch (e) {
                state.error = (e && e.message) || String(e) || "Bağlantı Hatası";
                state.connecting = false;
                setStatus("failed");
                notification.add(state.error, { type: "danger" });
                state.tokenData = null;
                return false;
            } finally {
                state.busy = false;
                starting = false;
            }
        }

        function toggleMute() {
            if (!activeCall) return;
            state.muted = !state.muted;
            activeCall.mute(state.muted);
        }

        function hangup() {
            try {
                activeCall?.disconnect?.();
            } catch (_) {}
            state.inCall = false;
            state.connecting = false;
            stopTimer();
            if (state.callStatus !== "completed") {
                setStatus("canceled");
            }
        }

        async function wrapup(payload = {}) {
            if (!state.callId) return { ok: false, error: { message: "Call ID missing" } };
            
            // Attach diagnostics
            payload.diagnostics = { ...state.diagnostics };
            
            return rpc(`/tcrm/voice/call/${state.callId}/wrapup`, payload);
        }
        
        function selectMicrophone(id) {
            state.selectedMicrophone = id;
            localStorage.setItem("santral_mic_id", id);
            setAudioDevices();
        }

        function selectSpeaker(id) {
            state.selectedSpeaker = id;
            localStorage.setItem("santral_speaker_id", id);
            setAudioDevices();
        }

        function sendDigits(digits) {
            try {
                activeCall?.sendDigits?.(String(digits));
            } catch (e) {
                console.warn("sendDigits failed", e);
            }
        }

        async function setSpeakerphone(on) {
            // Best-effort: route audio output to the default speaker device.
            try {
                if (device && device.audio && device.audio.speakerDevices) {
                    await device.audio.speakerDevices.set(on ? "default" : state.selectedSpeaker || "default");
                }
            } catch (e) {
                console.warn("setSpeakerphone failed", e);
            }
        }

        return {
            state,
            startCall,
            runPreflight,
            toggleMute,
            hangup,
            wrapup,
            selectMicrophone,
            selectSpeaker,
            sendDigits,
            setSpeakerphone,
            refreshDevices,
            bus,
            async checkMic() {
                try {
                    await refreshDevices();
                    state.micLabel = "İzin verildi";
                    return true;
                } catch (e) {
                    state.micLabel = "İzin reddedildi";
                    state.error = "Mikrofon izni gerekli.";
                    return false;
                }
            }
        };
    }
};

registry.category("services").add("call_center", callCenterServiceFactory);

export const callCenterService = {};
