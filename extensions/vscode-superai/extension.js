/**
 * SuperAI VS Code extension scaffold (N2).
 * Invokes the installed `superai` CLI via child_process.
 */
const vscode = require("vscode");
const { execFile } = require("child_process");

function runCli(args, cwd) {
  const cli = vscode.workspace.getConfiguration("superai").get("cliPath") || "superai";
  return new Promise((resolve, reject) => {
    execFile(cli, args, { cwd, maxBuffer: 2 * 1024 * 1024 }, (err, stdout, stderr) => {
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

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("superai.runTask", async () => {
      const task = await vscode.window.showInputBox({
        prompt: "SuperAI task",
        placeHolder: "Create a FastAPI hello world",
      });
      if (!task) return;
      const out = vscode.window.createOutputChannel("SuperAI");
      out.show(true);
      out.appendLine(`$ superai run ${JSON.stringify(task)}`);
      try {
        const stdout = await runCli(["run", task, "--format", "json"], getCwd());
        out.appendLine(stdout);
      } catch (e) {
        out.appendLine(String(e));
        vscode.window.showErrorMessage(`SuperAI failed: ${e.message}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("superai.doctor", async () => {
      const out = vscode.window.createOutputChannel("SuperAI");
      out.show(true);
      try {
        const stdout = await runCli(["doctor", "--quick"], getCwd());
        out.appendLine(stdout);
      } catch (e) {
        out.appendLine(String(e));
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("superai.chat", async () => {
      const msg = await vscode.window.showInputBox({ prompt: "Chat message" });
      if (!msg) return;
      const out = vscode.window.createOutputChannel("SuperAI");
      out.show(true);
      try {
        const stdout = await runCli(["chat", msg, "--new"], getCwd());
        out.appendLine(stdout);
      } catch (e) {
        out.appendLine(String(e));
      }
    })
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
