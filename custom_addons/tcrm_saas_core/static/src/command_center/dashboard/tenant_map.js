/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useRef, useState, onMounted, onPatched, onWillUnmount } from "@tcrm/owl";

const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

let leafletPromise = null;

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function loadLeaflet() {
    if (window.L) {
        return Promise.resolve();
    }
    if (!leafletPromise) {
        leafletPromise = new Promise((resolve, reject) => {
            const s = document.createElement("script");
            s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
            s.async = true;
            s.onload = () => resolve();
            s.onerror = () => reject(new Error("Leaflet load failed"));
            document.head.appendChild(s);
        });
    }
    return leafletPromise;
}

export class TcrmTenantMap extends Component {
    static template = "tcrm_saas_core.TenantMap";
    static props = {
        markers: { type: Array, optional: true },
        title: String,
        onMarkerSelect: { type: Function, optional: true },
        onMarkerMoved: { type: Function, optional: true },
        draggable: { type: Boolean, optional: true },
    };

    setup() {
        this.rootRef = useRef("map");
        this._map = null;
        this._markersLayer = null;
        this._searchMarker = null;
        this._ready = false;
        this._searchTimer = null;

        this.state = useState({
            searchQuery: "",
            searchResults: null,
        });

        onMounted(() => this._scheduleInit());
        onPatched(() => this._scheduleInit());
        onWillUnmount(() => this._teardown());
    }

    // ── Map lifecycle ────────────────────────────────────────────────────

    _scheduleInit() {
        queueMicrotask(() => this._initMap());
    }

    async _initMap() {
        const el = this.rootRef.el;
        const markers = this.props.markers || [];
        if (!el) {
            return;
        }
        if (!markers.length && !this._map) {
            // Still initialize map even with no markers so user can search
        }

        try {
            await loadLeaflet();
        } catch {
            el.textContent = _t("Map unavailable.");
            return;
        }
        const L = window.L;
        if (!L) {
            return;
        }

        if (!this._map) {
            el.innerHTML = "";
            this._map = L.map(el, {
                zoomControl: false,
                attributionControl: true,
            }).setView([37.2, 35.2], 5);
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution: OSM_ATTR,
            }).addTo(this._map);
            this._markersLayer = L.layerGroup().addTo(this._map);
        }

        this._markersLayer.clearLayers();
        const latLngs = [];
        const isDraggable = !!this.props.draggable;
        for (const m of markers) {
            const hasReal = !!m.has_real_coords;
            const popupHtml = `
                <div style="min-width:160px">
                    <strong>${escapeHtml(m.name)}</strong>
                    ${m.is_frozen ? `<br/><span style="color:#dc3545;font-size:11px">🔒 FROZEN</span>` : ""}
                    ${m.address ? `<br/><small style="color:#6c757d">${escapeHtml(m.address)}</small>` : ""}
                    ${!hasReal ? `<br/><small style="color:#adb5bd;font-style:italic">Estimated location</small>` : ""}
                    <br/><a href="#" onclick="return false;" style="font-size:11px" id="mk-open-${m.id}">
                        Open Tenant 360 →
                    </a>
                </div>`;
            const mk = L.marker([m.lat, m.lon], { draggable: isDraggable });
            mk.bindPopup(popupHtml, { maxWidth: 260 });
            mk.on("click", () => {
                if (this.props.onMarkerSelect) {
                    this.props.onMarkerSelect(m.id);
                }
            });
            if (isDraggable && this.props.onMarkerMoved) {
                mk.on("dragend", (ev) => {
                    const { lat, lng } = ev.target.getLatLng();
                    this.props.onMarkerMoved({ id: m.id, lat, lon: lng });
                });
            }
            mk.addTo(this._markersLayer);
            latLngs.push([m.lat, m.lon]);
        }
        if (latLngs.length === 1) {
            this._map.setView(latLngs[0], 6);
        } else if (latLngs.length) {
            this._map.fitBounds(latLngs, { padding: [28, 28], maxZoom: 7 });
        }
        requestAnimationFrame(() => this._map?.invalidateSize());
        this._ready = true;
    }

    _teardown() {
        if (this._map) {
            try {
                this._map.remove();
            } catch {
                /* ignore */
            }
        }
        this._map = null;
        this._markersLayer = null;
        this._searchMarker = null;
        this._ready = false;
    }

    // ── Zoom controls ────────────────────────────────────────────────────

    zoomIn() {
        this._map?.zoomIn();
    }

    zoomOut() {
        this._map?.zoomOut();
    }

    fitAllMarkers() {
        if (!this._map) {
            return;
        }
        const markers = this.props.markers || [];
        if (!markers.length) {
            this._map.setView([37.2, 35.2], 5);
            return;
        }
        const latLngs = markers.map((m) => [m.lat, m.lon]);
        this._map.fitBounds(latLngs, { padding: [28, 28], maxZoom: 7 });
    }

    // ── Address search (Nominatim geocoding) ─────────────────────────────

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        if (this._searchTimer) {
            clearTimeout(this._searchTimer);
        }
        const q = (this.state.searchQuery || "").trim();
        if (q.length < 3) {
            this.state.searchResults = null;
            return;
        }
        this._searchTimer = setTimeout(() => this._geocode(q), 400);
    }

    onSearchKeydown(ev) {
        if (ev.key === "Escape") {
            this.clearSearch();
        }
        if (ev.key === "Enter") {
            ev.preventDefault();
            const q = (this.state.searchQuery || "").trim();
            if (q.length >= 3) {
                this._geocode(q);
            }
        }
    }

    clearSearch() {
        this.state.searchQuery = "";
        this.state.searchResults = null;
        if (this._searchMarker && this._map) {
            this._map.removeLayer(this._searchMarker);
            this._searchMarker = null;
        }
    }

    async _geocode(query) {
        try {
            const url = `${NOMINATIM_URL}?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`;
            const resp = await fetch(url, {
                headers: { "Accept-Language": "en" },
            });
            const data = await resp.json();
            this.state.searchResults = (data || []).map((r) => ({
                lat: parseFloat(r.lat),
                lon: parseFloat(r.lon),
                display_name: r.display_name,
            }));
        } catch {
            this.state.searchResults = [];
        }
    }

    selectSearchResult(result) {
        if (!this._map || !window.L) {
            return;
        }
        const L = window.L;
        if (this._searchMarker) {
            this._map.removeLayer(this._searchMarker);
        }
        this._searchMarker = L.marker([result.lat, result.lon], {
            icon: L.divIcon({
                className: "",
                html: '<div style="background:#e63946;color:#fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.3)"><i class="fa fa-crosshairs"></i></div>',
                iconSize: [28, 28],
                iconAnchor: [14, 14],
            }),
        }).addTo(this._map);
        this._searchMarker.bindPopup(`<strong>${escapeHtml(result.display_name)}</strong>`).openPopup();
        this._map.setView([result.lat, result.lon], 14);
        this.state.searchResults = null;
    }
}
