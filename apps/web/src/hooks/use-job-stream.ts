"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PipelineState } from "@ebook/shared";

import { apiBaseUrl, tokenStore } from "@/lib/api/client";

type StreamStatus = "idle" | "connecting" | "open" | "closed" | "error";

interface DoneEvent {
  job_id: string;
  status: string;
  error: string | null;
  progress_pct: number;
}

interface UseJobStreamResult {
  state: PipelineState | null;
  status: StreamStatus;
  error: string | null;
  done: DoneEvent | null;
}

/**
 * Subscribe to a job's Server-Sent Events stream.
 *
 * `EventSource` cannot send an Authorization header, so we stream the response
 * with `fetch` and parse the SSE frames ourselves. The stream closes as soon as
 * the job reaches a terminal state.
 */
export function useJobStream(jobId: string | null | undefined, enabled = true): UseJobStreamResult {
  const [state, setState] = useState<PipelineState | null>(null);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<DoneEvent | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleFrame = useCallback((chunk: string) => {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of chunk.split("\n")) {
      if (line.startsWith(":")) continue; // heartbeat comment
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    const raw = dataLines.join("\n");
    if (!raw) return;
    let payload: unknown;
    try {
      payload = JSON.parse(raw);
    } catch {
      return;
    }
    if (event === "snapshot" || event === "progress") {
      setState(payload as PipelineState);
    } else if (event === "done") {
      setDone(payload as DoneEvent);
      setStatus("closed");
    } else if (event === "error") {
      setError((payload as { message?: string }).message ?? "Job error");
      setStatus("error");
    }
  }, []);

  const start = useCallback(
    async (id: string, signal: AbortSignal) => {
      setStatus("connecting");
      setError(null);
      try {
        const response = await fetch(`${apiBaseUrl()}/api/v1/jobs/${id}/events`, {
          headers: {
            Accept: "text/event-stream",
            ...(tokenStore.access() ? { Authorization: `Bearer ${tokenStore.access()}` } : {}),
          },
          credentials: "include",
          signal,
        });
        if (!response.ok || !response.body) {
          throw new Error(`Stream failed (${response.status})`);
        }
        setStatus("open");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done: finished, value } = await reader.read();
          if (finished) break;
          buffer += decoder.decode(value, { stream: true });

          let boundary = buffer.indexOf("\n\n");
          while (boundary !== -1) {
            const chunk = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            handleFrame(chunk);
            boundary = buffer.indexOf("\n\n");
          }
        }
        setStatus("closed");
      } catch (err) {
        if (signal.aborted) return;
        setStatus("error");
        setError(err instanceof Error ? err.message : "Stream error");
      }
    },
    [handleFrame],
  );

  useEffect(() => {
    if (!jobId || !enabled) {
      setStatus("idle");
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setDone(null);
    void start(jobId, controller.signal);
    return () => controller.abort();
  }, [jobId, enabled, start]);

  return { state, status, error, done };
}
