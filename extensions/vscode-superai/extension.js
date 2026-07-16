/**
 * SuperAI VS Code extension — W7 full depth.
 *
 * Shells out to the SuperAI CLI with:
 * - Output channel + status bar
 * - Ask / Do / Review / Doctor / Members / Smoke / Status / Plugin catalog
 * - Editor selection → ask/review
 * - Integrated terminal for agent-tui
 * - Insert last CLI output into editor
 *
 * Pure CLI helpers live in lib/cli.js (unit-tested without VS Code host).
 */
"use strict";

const vscode = require("vscode");
const {
  runSuperaiCli,
  buildArgs,
  parseCliOutput,
  formatResult,
} = require("./lib/cli");

/** @type {string} */
let lastOutput = "";
/** @type {import('vscode').StatusBarItem | undefined} */
let statusBar;
/** @type {import('vscode').OutputChannel | undefined} */
let channel;

function getConfig() {
  const cfg = vscode.workspace.getConfiguration("superai");
  return {
    cliPath: cfg.get("cliPath") || "superai",
    timeoutMs: Number(cfg.get("timeoutMs") || 180000),
    mockMode: Boolean(cfg.get("mockMode")),
    autoShowOutput: cfg.get("autoShowOutput") !== false,
    pythonPath: cfg.get("pythonPath") || "",
  };
}

function getCwd() {
  const folders = vscode.workspace.workspaceFolders;
  return folders && folders[0] ? folders[0].uri.fsPath : undefined;
}

function getChannel() {
  if (!channel) {
    channel = vscode.window.createOutputChannel("SuperAI");
  }
  return channel;
}

function setStatus(text, tooltip) {
  if (!statusBar) return;
  statusBar.text = text;
  statusBar.tooltip = tooltip || "SuperAI";
  statusBar.show();
}

/**
 * @param {string[]} args
 * @param {{title?: string, insert?: boolean}} [opts]
 */
async function runAndShow(args, opts) {
  const o = opts || {};
  const conf = getConfig();
  const out = getChannel();
  if (conf.autoShowOutput) out.show(true);

  const env = {};
  if (conf.mockMode) {
    env.SUPERAI_MOCK = "1";
    env.SUPERAI_USE_MOCK = "1";
  }
  if (conf.pythonPath) {
    env.PYTHONPATH = conf.pythonPath;
  }

  setStatus("$(sync~spin) SuperAI…", args.join(" "));
  out.appendLine("");
  out.appendLine(`—— ${new Date().toISOString()} ——`);

  const result = await runSuperaiCli({
    cliPath: conf.cliPath,
    args,
    cwd: getCwd(),
    timeoutMs: conf.timeoutMs,
    env,
  });

  const formatted = formatResult(result);
  out.appendLine(formatted);
  lastOutput = result.stdout || result.stderr || formatted;

  if (result.ok) {
    setStatus("$(check) SuperAI", "Last command succeeded");
    const parsed = parseCliOutput(result.stdout);
    if (parsed.json && parsed.json.ok === false) {
      vscode.window.showWarningMessage(
        `SuperAI returned ok=false: ${String(parsed.json.error || parsed.json.status || "").slice(0, 120)}`
      );
    } else {
      vscode.window.setStatusBarMessage(`SuperAI: ${o.title || args[0]} done`, 4000);
    }
  } else {
    setStatus("$(error) SuperAI", result.error || "failed");
    vscode.window.showErrorMessage(
      `SuperAI failed: ${(result.error || result.stderr || "error").slice(0, 200)}`
    );
  }

  if (o.insert && lastOutput) {
    await insertText(lastOutput);
  }
  return result;
}

async function insertText(text) {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    const doc = await vscode.workspace.openTextDocument({
      content: String(text).slice(0, 200000),
      language: "json",
    });
    await vscode.window.showTextDocument(doc);
    return;
  }
  await editor.edit((eb) => {
    const sel = editor.selection;
    if (!sel.isEmpty) {
      eb.replace(sel, String(text));
    } else {
      eb.insert(sel.active, String(text));
    }
  });
}

function selectionText() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return "";
  const t = editor.document.getText(editor.selection);
  return (t || "").trim();
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  statusBar.text = "$(rocket) SuperAI";
  statusBar.tooltip = "SuperAI VS Code extension (W7)";
  statusBar.command = "superai.status";
  statusBar.show();
  context.subscriptions.push(statusBar);
  context.subscriptions.push(getChannel());

  /** @type {[string, () => Promise<void>][]} */
  const cmds = [
    [
      "superai.runTask",
      async () => {
        const task = await vscode.window.showInputBox({
          prompt: "SuperAI task",
          placeHolder: "Create a FastAPI hello world",
        });
        if (!task) return;
        await runAndShow(buildArgs("run", { text: task }), { title: "run" });
      },
    ],
    [
      "superai.do",
      async () => {
        const task = await vscode.window.showInputBox({
          prompt: "SuperAI do (one-shot front door)",
          placeHolder: "summarize this repo",
        });
        if (!task) return;
        await runAndShow(buildArgs("do", { text: task }), { title: "do" });
      },
    ],
    [
      "superai.doctor",
      async () => {
        await runAndShow(buildArgs("doctor", { quick: true }), { title: "doctor" });
      },
    ],
    [
      "superai.status",
      async () => {
        await runAndShow(buildArgs("status", { cost: true }), { title: "status" });
      },
    ],
    [
      "superai.chat",
      async () => {
        const msg = await vscode.window.showInputBox({ prompt: "Chat message" });
        if (!msg) return;
        await runAndShow(buildArgs("chat", { text: msg }), { title: "chat" });
      },
    ],
    [
      "superai.ask",
      async () => {
        const msg = await vscode.window.showInputBox({
          prompt: "Ask SuperAI (NL front door)",
          placeHolder: "review the auth design dry-run",
        });
        if (!msg) return;
        await runAndShow(buildArgs("ask", { text: msg }), { title: "ask" });
      },
    ],
    [
      "superai.askSelection",
      async () => {
        let text = selectionText();
        if (!text) {
          text = await vscode.window.showInputBox({
            prompt: "No selection — enter text to ask about",
          });
        }
        if (!text) return;
        const prompt = `Regarding the following code/text:\n\n${text.slice(0, 12000)}\n\nExplain and suggest next steps.`;
        await runAndShow(buildArgs("ask", { text: prompt }), { title: "askSelection" });
      },
    ],
    [
      "superai.review",
      async () => {
        const subj = await vscode.window.showInputBox({
          prompt: "Review subject",
          placeHolder: "auth middleware",
        });
        if (!subj) return;
        await runAndShow(buildArgs("review", { text: subj }), { title: "review" });
      },
    ],
    [
      "superai.reviewSelection",
      async () => {
        let text = selectionText();
        if (!text) {
          vscode.window.showWarningMessage("Select code to review first.");
          return;
        }
        const subj = `Review this code:\n${text.slice(0, 12000)}`;
        await runAndShow(buildArgs("review", { text: subj }), {
          title: "reviewSelection",
        });
      },
    ],
    [
      "superai.members",
      async () => {
        await runAndShow(buildArgs("members"), { title: "members" });
      },
    ],
    [
      "superai.smokePreflight",
      async () => {
        await runAndShow(buildArgs("smoke-preflight"), { title: "smoke-preflight" });
      },
    ],
    [
      "superai.pluginCatalog",
      async () => {
        const q = await vscode.window.showInputBox({
          prompt: "Plugin catalog query (empty = status)",
          placeHolder: "memory",
        });
        const args = q
          ? buildArgs("plugin-catalog", { query: q })
          : buildArgs("plugin-catalog", {});
        await runAndShow(args, { title: "plugin-catalog" });
      },
    ],
    [
      "superai.progress",
      async () => {
        await runAndShow(buildArgs("progress"), { title: "progress" });
      },
    ],
    [
      "superai.v6Status",
      async () => {
        await runAndShow(buildArgs("v6-status"), { title: "v6-status" });
      },
    ],
    [
      "superai.explainRun",
      async () => {
        const runId = await vscode.window.showInputBox({
          prompt: "run_id to explain",
          placeHolder: "run-…",
        });
        if (!runId) return;
        await runAndShow(buildArgs("explain-run", { runId }), { title: "explain-run" });
      },
    ],
    [
      "superai.openAgentTerminal",
      async () => {
        const conf = getConfig();
        const term = vscode.window.createTerminal({
          name: "SuperAI Agent",
          cwd: getCwd(),
        });
        term.show();
        // quote path if spaces
        const cli = conf.cliPath.includes(" ")
          ? `"${conf.cliPath}"`
          : conf.cliPath;
        term.sendText(`${cli} agent`);
      },
    ],
    [
      "superai.insertLastOutput",
      async () => {
        if (!lastOutput) {
          vscode.window.showInformationMessage("No SuperAI output yet.");
          return;
        }
        await insertText(lastOutput);
      },
    ],
    [
      "superai.agentTuiHint",
      async () => {
        vscode.window.showInformationMessage(
          "SuperAI Agent: command SuperAI: Open Agent Terminal  ·  or run: superai agent"
        );
      },
    ],
  ];

  for (const [id, fn] of cmds) {
    context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  }
}

function deactivate() {
  if (statusBar) statusBar.dispose();
  if (channel) channel.dispose();
}

module.exports = {
  activate,
  deactivate,
  // exported for tests / diagnostics
  _internal: { getConfig, getCwd, buildArgs, runSuperaiCli, parseCliOutput },
};
