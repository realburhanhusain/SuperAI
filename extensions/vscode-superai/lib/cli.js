/**
 * SuperAI CLI runner (testable without VS Code host).
 * W7 — pure Node helpers used by extension.js
 */
"use strict";

const { execFile } = require("child_process");
const path = require("path");

/**
 * @param {object} opts
 * @param {string} opts.cliPath
 * @param {string[]} opts.args
 * @param {string} [opts.cwd]
 * @param {number} [opts.timeoutMs]
 * @param {Record<string,string>} [opts.env]
 * @returns {Promise<{ok:boolean, stdout:string, stderr:string, code:number|null, args:string[], cliPath:string}>}
 */
function runSuperaiCli(opts) {
  const cliPath = opts.cliPath || "superai";
  const args = Array.isArray(opts.args) ? opts.args.slice() : [];
  const cwd = opts.cwd || process.cwd();
  const timeoutMs = typeof opts.timeoutMs === "number" ? opts.timeoutMs : 120000;
  const env = Object.assign({}, process.env, opts.env || {});

  return new Promise((resolve) => {
    execFile(
      cliPath,
      args,
      {
        cwd,
        env,
        timeout: timeoutMs,
        maxBuffer: 8 * 1024 * 1024,
        windowsHide: true,
      },
      (err, stdout, stderr) => {
        const out = String(stdout || "");
        const errS = String(stderr || "");
        if (err) {
          resolve({
            ok: false,
            stdout: out,
            stderr: errS || err.message || String(err),
            code: typeof err.code === "number" ? err.code : 1,
            args,
            cliPath,
            error: err.message || String(err),
          });
          return;
        }
        resolve({
          ok: true,
          stdout: out,
          stderr: errS,
          code: 0,
          args,
          cliPath,
        });
      }
    );
  });
}

/**
 * Build CLI argv for a named SuperAI action.
 * Pure function for unit tests.
 *
 * @param {string} action
 * @param {object} [params]
 * @returns {string[]}
 */
function buildArgs(action, params) {
  const p = params || {};
  const a = String(action || "").toLowerCase();
  switch (a) {
    case "doctor":
      return p.quick === false ? ["doctor"] : ["doctor", "--quick"];
    case "status":
      return p.cost ? ["status", "--cost"] : ["status"];
    case "members":
      return ["members", "--available"];
    case "smoke-preflight":
    case "smokepreflight":
      return p.readiness ? ["smoke-preflight", "--readiness"] : ["smoke-preflight"];
    case "ask":
      return ["ask", String(p.text || ""), "--format", "json"];
    case "do":
      return ["do", String(p.text || "")];
    case "run":
      return ["run", String(p.text || ""), "--format", "json"];
    case "chat":
      return ["chat", String(p.text || ""), "--new"];
    case "review":
      return ["review", String(p.text || ""), "--dry-run", "--format", "json"];
    case "plugin-catalog":
      return p.query
        ? ["plugin-catalog", "-q", String(p.query)]
        : ["plugin-catalog", "--status"];
    case "progress":
      return ["progress"];
    case "v6-status":
      return ["v6-status"];
    case "explain-run":
      return ["explain-run", String(p.runId || "")];
    case "voice-status":
      return ["voice", "status"];
    case "foundation-check":
      return ["foundation-check", "all"];
    default:
      throw new Error(`unknown_action:${action}`);
  }
}

/**
 * Try parse JSON stdout; else return text envelope.
 * @param {string} stdout
 */
function parseCliOutput(stdout) {
  const s = String(stdout || "").trim();
  if (!s) {
    return { ok: true, empty: true, raw: "" };
  }
  try {
    return { ok: true, json: JSON.parse(s), raw: s };
  } catch (_) {
    // try last JSON object in output
    const m = s.match(/\{[\s\S]*\}\s*$/);
    if (m) {
      try {
        return { ok: true, json: JSON.parse(m[0]), raw: s };
      } catch (_) {
        /* fallthrough */
      }
    }
    return { ok: true, text: s, raw: s };
  }
}

/**
 * Format result for output channel.
 * @param {{ok:boolean, stdout:string, stderr:string, args:string[], cliPath:string, error?:string}} result
 */
function formatResult(result) {
  const lines = [];
  lines.push(`$ ${result.cliPath} ${result.args.join(" ")}`);
  if (result.stdout) lines.push(result.stdout);
  if (result.stderr) lines.push(`[stderr]\n${result.stderr}`);
  if (!result.ok) lines.push(`[failed] ${result.error || result.stderr || "error"}`);
  return lines.join("\n");
}

/**
 * Validate package contributes.commands ids match expected W7 set.
 * @param {object} pkg package.json object
 */
function validatePackageCommands(pkg) {
  const required = [
    "superai.runTask",
    "superai.doctor",
    "superai.chat",
    "superai.ask",
    "superai.do",
    "superai.review",
    "superai.members",
    "superai.smokePreflight",
    "superai.status",
    "superai.pluginCatalog",
    "superai.askSelection",
    "superai.reviewSelection",
    "superai.openAgentTerminal",
    "superai.insertLastOutput",
  ];
  const cmds = ((pkg && pkg.contributes && pkg.contributes.commands) || []).map(
    (c) => c.command
  );
  const missing = required.filter((r) => !cmds.includes(r));
  return {
    ok: missing.length === 0,
    missing,
    count: cmds.length,
    required: required.length,
  };
}

module.exports = {
  runSuperaiCli,
  buildArgs,
  parseCliOutput,
  formatResult,
  validatePackageCommands,
};
