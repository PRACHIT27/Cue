"use client";

import { useEffect, useRef, useState } from "react";
import { get } from "../lib/api";

const LEAFLET = "https://unpkg.com/leaflet@1.9.4/dist/leaflet";
const AREAS = ["United States", "Canada", "United Kingdom", "India"];
const VIEWS = {
  "United States": [[24, -125], [50, -66]],
  Canada: [[42, -141], [60, -52]],
  "United Kingdom": [[49.8, -8.5], [59, 2]],
  India: [[6, 68], [35, 97]],
};

function loadLeaflet() {
  if (typeof window === "undefined") return Promise.reject(new Error("no window"));
  if (window.L) return Promise.resolve(window.L);
  if (window.__leafletLoading) return window.__leafletLoading;
  window.__leafletLoading = new Promise((resolve, reject) => {
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = `${LEAFLET}.css`;
    document.head.appendChild(css);
    const script = document.createElement("script");
    script.src = `${LEAFLET}.js`;
    script.onload = () => resolve(window.L);
    script.onerror = () => reject(new Error("The map library didn't load"));
    document.head.appendChild(script);
  });
  return window.__leafletLoading;
}

export default function FanMap({ artistId }) {
  const [area, setArea] = useState(AREAS[0]);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const box = useRef(null);
  const map = useRef(null);
  const layer = useRef(null);

  useEffect(() => {
    let live = true;
    setBusy(true);
    setError("");
    get(`/artists/${artistId}/map?area=${encodeURIComponent(area)}`)
      .then((body) => live && setData(body))
      .catch((failure) => live && setError(failure.message))
      .finally(() => live && setBusy(false));
    return () => {
      live = false;
    };
  }, [artistId, area]);

  useEffect(() => {
    if (!data || !box.current) return;
    let cancelled = false;
    loadLeaflet()
      .then((L) => {
        if (cancelled || !box.current) return;
        if (!map.current) {
          map.current = L.map(box.current, { scrollWheelZoom: false, attributionControl: true });
          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 12,
            attribution: "&copy; OpenStreetMap contributors",
          }).addTo(map.current);
        }
        if (layer.current) layer.current.remove();
        layer.current = L.layerGroup().addTo(map.current);
        const top = Math.max(...data.points.map((p) => p.affinity), 0.0001);
        data.points.forEach((p) => {
          const strength = p.affinity / top;
          L.circleMarker([p.lat, p.lon], {
            radius: 3 + strength * 9,
            stroke: false,
            fillColor: strength > 0.85 ? "#4f3cf0" : "#8f82f6",
            fillOpacity: 0.15 + strength * 0.55,
          }).addTo(layer.current);
        });
        const view = VIEWS[area] || VIEWS["United States"];
        setTimeout(() => {
          if (!map.current) return;
          map.current.invalidateSize();
          map.current.fitBounds(view);
        }, 60);
      })
      .catch((failure) => setError(failure.message));
    return () => {
      cancelled = true;
    };
  }, [data, area]);

  const empty = data && data.points.length < 3;
  return (
    <section className="card stack">
      <div className="between">
        <div className="stack" style={{ gap: 4 }}>
          <h3>Where your fans are</h3>
          <p className="muted small">Qloo's heatmap of people whose taste matches your fans. Darker, bigger dots mean a stronger match.</p>
        </div>
        <label className="sr-only" htmlFor="map-area">Area</label>
        <select id="map-area" className="input" style={{ width: "auto" }} value={area} onChange={(e) => setArea(e.target.value)}>
          {AREAS.map((a) => <option key={a}>{a}</option>)}
        </select>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {busy && <p className="muted small">Asking Qloo…</p>}
      {empty && <p className="note">Qloo doesn't have enough taste data to map fans in {area} yet. Try another area.</p>}
      <div ref={box} style={{ height: 340, borderRadius: 12, overflow: "hidden", display: empty ? "none" : "block", background: "#eef0f6" }} />
      {data && data.top_areas.length > 0 && (
        <div className="stack" style={{ gap: 6 }}>
          <strong className="small">Strongest areas</strong>
          <div className="rank-list">
            {data.top_areas.map((a, index) => (
              <div className="rank-row" key={a.name}>
                <span className="rank-num">{index + 1}</span>
                <span className="rank-name">{a.name}</span>
                <span className="rank-bar"><span style={{ width: `${Math.round((a.affinity || 0) * 100)}%` }} /></span>
                <span className="rank-val">{Math.round((a.affinity || 0) * 100)}</span>
              </div>
            ))}
          </div>
          <p className="muted small">Named by the nearest big city to each hot spot.</p>
        </div>
      )}
    </section>
  );
}
