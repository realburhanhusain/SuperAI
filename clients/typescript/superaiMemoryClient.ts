/**
 * Thin SuperAI Memory client (Phase 9+).
 *
 * Default transport: spawn `superai --json …` (Node child_process).
 * Does not open SuperAI database files.
 *
 * Usage (Node 18+):
 *   import { SuperAIMemoryClient } from "./superaiMemoryClient";
 *   const c = new SuperAIMemoryClient();
 *   console.log(await c.recall("Cloud SQL"));
 */

import { spawn } from "node:child_process";

export type JsonEnvelope = {
  ok?: boolean;
  error?: string;
  error_code?: string;
  message?: string;
  [key: string]: unknown;
};

export class SuperAIMemoryClient {
  binary: string;
  timeoutMs: number;

  constructor(opts?: { binary?: string; timeoutMs?: number }) {
    this.binary = opts?.binary || process.env.SUPERAI_BIN || "superai";
    this.timeoutMs = opts?.timeoutMs ?? 120_000;
  }

  private run(args: string[]): Promise<JsonEnvelope> {
    return new Promise((resolve) => {
      const child = spawn(this.binary, ["--json", ...args], {
        env: process.env,
        windowsHide: true,
      });
      let stdout = "";
      let stderr = "";
      const timer = setTimeout(() => {
        child.kill();
        resolve({ ok: false, error: "timeout", error_code: "timeout" });
      }, this.timeoutMs);
      child.stdout.on("data", (d) => (stdout += d.toString()));
      child.stderr.on("data", (d) => (stderr += d.toString()));
      child.on("error", (err) => {
        clearTimeout(timer);
        resolve({
          ok: false,
          error: String(err.message || err),
          error_code: "not_found",
        });
      });
      child.on("close", () => {
        clearTimeout(timer);
        const text = stdout.trim();
        if (!text) {
          resolve({
            ok: false,
            error: stderr.slice(0, 400) || "empty stdout",
          });
          return;
        }
        try {
          resolve(JSON.parse(text) as JsonEnvelope);
        } catch {
          const lines = text.split(/\r?\n/).reverse();
          for (const line of lines) {
            if (line.trim().startsWith("{")) {
              try {
                resolve(JSON.parse(line) as JsonEnvelope);
                return;
              } catch {
                /* continue */
              }
            }
          }
          resolve({ ok: false, error: "non-json output", raw: text.slice(0, 500) });
        }
      });
    });
  }

  recall(query: string, strategy = "auto", topK = 10): Promise<JsonEnvelope> {
    return this.run(["recall", query, "--strategy", strategy, "--top-k", String(topK)]);
  }

  cognify(source: string, mode = "mock", dataset = "default"): Promise<JsonEnvelope> {
    return this.run(["cognify", source, "--mode", mode, "--dataset", dataset]);
  }

  kgStatus(): Promise<JsonEnvelope> {
    return this.run(["kg", "status"]);
  }

  datasetList(): Promise<JsonEnvelope> {
    return this.run(["dataset", "list"]);
  }

  memoryEval(): Promise<JsonEnvelope> {
    return this.run(["memory-eval"]);
  }

  otelStatus(): Promise<JsonEnvelope> {
    return this.run(["otel", "status"]);
  }

  cloudStatus(): Promise<JsonEnvelope> {
    return this.run(["cloud", "status"]);
  }

  hostHookEmit(event: string, content = "", session?: string): Promise<JsonEnvelope> {
    const args = ["host-hook", "emit", event];
    if (content) args.push("--content", content);
    if (session) args.push("--session", session);
    return this.run(args);
  }
}
