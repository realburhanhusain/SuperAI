/**
 * SuperAI VS Code extension (N2 + not-important W7 depth).
 * Invokes the installed `superai` CLI via child_process.
 */
const vscode = require("vscode");
const { execFile } = require("child_process");

function runCli(args, cwd) {
  const cli = vscode.workspace.getConfiguration("superai").get("cliPath") || "superai";
  return new Promise((resolve, reject) => {
    execFile(cli, args, { cwd, maxBuffer: 4 * 1024 * 1024 }, (err, stdout, stderr) => {
      if (err) {
        reject(new Error(stderr || err.message));
        return;
      }
      resolve(stdout || "");
    });
  });
}

function getCwd() {
  const folders = vscode.workspace.workspaceFolders;
  return folders && folders[0] ? folders[0].uri.fsPath : undefined;
}

async function showOut(title, args) {
  const out = vscode.window.createOutputChannel("SuperAI");
  out.show(true);
  out.appendLine(`$ superai ${args.join(" ")}`);
  try {
    const stdout = await runCli(args, getCwd());
    out.appendLine(stdout);
  } catch (e) {
    out.appendLine(String(e));
    vscode.window.showErrorMessage(`SuperAI failed: ${e.message}`);
  }
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  const cmds = [
    [
      "superai.runTask",
      async () => {
        const task = await vscode.window.showInputBox({
          prompt: "SuperAI task",
          placeHolder: "Create a FastAPI hello world",
        });
        if (!task) return;
        await showOut("run", ["run", task, "--format", "json"]);
      },
    ],
    [
      "superai.doctor",
      async () => {
        await showOut("doctor", ["doctor", "--quick"]);
      },
    ],
    [
      "superai.chat",
      async () => {
        const msg = await vscode.window.showInputBox({ prompt: "Chat message" });
        if (!msg) return;
        await showOut("chat", ["chat", msg, "--new"]);
      },
    ],
    // W7 depth
    [
      "superai.ask",
      async () => {
        const msg = await vscode.window.showInputBox({
          prompt: "Ask SuperAI (NL front door)",
          placeHolder: "review the auth design dry-run",
        });
        if (!msg) return;
        await showOut("ask", ["ask", msg, "--format", "json"]);
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
        await showOut("review", ["review", subj, "--dry-run", "--format", "json"]);
      },
    ],
    [
      "superai.members",
      async () => {
        await showOut("members", ["members", "--available"]);
      },
    ],
    [
      "superai.smokePreflight",
      async () => {
        await showOut("smoke-preflight", ["smoke-preflight"]);
      },
    ],
    [
      "superai.agentTuiHint",
      async () => {
        vscode.window.showInformationMessage(
          "Run in terminal: superai agent-tui  (slash: /export /undo /paste /cost)"
        );
      },
    ],
  ];

  for (const [id, fn] of cmds) {
    context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
