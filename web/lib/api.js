"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export const API = (process.env.NEXT_PUBLIC_CUE_API || "http://localhost:8000").replace(/\/$/, "");

const EVENT_KINDS = ["onboarding", "step_start", "step_end", "qloo_call", "guard_drop", "result", "error", "run_end"];

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = body && body.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || `Cue's server answered ${response.status}`;
    throw new Error(message);
  }
  return body;
}

export const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body) });
export const get = (path) => request(path);

export function useRun() {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("idle");
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const source = useRef(null);

  const close = () => {
    if (source.current) {
      source.current.close();
      source.current = null;
    }
  };

  useEffect(() => close, []);

  const start = useCallback(async (body) => {
    close();
    setEvents([]);
    setSummary(null);
    setError("");
    setStatus("running");
    try {
      const run = await post("/runs", body);
      const stream = new EventSource(`${API}${run.events}`);
      source.current = stream;
      const finish = async () => {
        close();
        try {
          const done = await get(run.result);
          setSummary(done);
          setStatus(done.status);
          if (done.status === "error") setError(done.error || "The run failed.");
        } catch (failure) {
          setError(failure.message);
          setStatus("error");
        }
      };
      EVENT_KINDS.forEach((kind) =>
        stream.addEventListener(kind, (message) => {
          const event = JSON.parse(message.data);
          setEvents((list) => (list.some((e) => e.seq === event.seq) ? list : [...list, event]));
          if (kind === "run_end") finish();
        })
      );
      stream.onerror = () => {
        if (stream.readyState === EventSource.CLOSED) finish();
      };
    } catch (failure) {
      setError(failure.message);
      setStatus("error");
    }
  }, []);

  return { events, status, summary, error, start };
}
