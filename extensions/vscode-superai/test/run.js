/**
 * Node unit tests for SuperAI VS Code extension (no VS Code host required).
 * Run: node test/run.js   OR   npm test
 */
"use strict";

const assert = require("assert");
const path = require("path");
const fs = require("fs");

const cli = require("../lib/cli");

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed += 1;
    console.log(`  ok  ${name}`);
  } catch (e) {
    failed += 1;
    console.error(`  FAIL ${name}`);
    console.error(`       ${e && e.stack ? e.stack : e}`);
  }
}

console.log("vscode-superai W7 tests\n");

test("buildArgs doctor quick", () => {
  assert.deepStrictEqual(cli.buildArgs("doctor"), ["doctor", "--quick"]);
  assert.deepStrictEqual(cli.buildArgs("doctor", { quick: false }), ["doctor"]);
});

test("buildArgs ask/do/run/review", () => {
  assert.deepStrictEqual(cli.buildArgs("ask", { text: "hi" }), [
    "ask",
    "hi",
    "--format",
    "json",
  ]);
  assert.deepStrictEqual(cli.buildArgs("do", { text: "x" }), ["do", "x"]);
  assert.deepStrictEqual(cli.buildArgs("run", { text: "t" }), [
    "run",
    "t",
    "--format",
    "json",
  ]);
  assert.deepStrictEqual(cli.buildArgs("review", { text: "auth" }), [
    "review",
    "auth",
    "--dry-run",
    "--format",
    "json",
  ]);
});

test("buildArgs members smoke status plugin", () => {
  assert.deepStrictEqual(cli.buildArgs("members"), ["members", "--available"]);
  assert.deepStrictEqual(cli.buildArgs("smoke-preflight"), ["smoke-preflight"]);
  assert.deepStrictEqual(cli.buildArgs("status", { cost: true }), [
    "status",
    "--cost",
  ]);
  assert.deepStrictEqual(cli.buildArgs("plugin-catalog", {}), [
    "plugin-catalog",
    "--status",
  ]);
  assert.deepStrictEqual(cli.buildArgs("plugin-catalog", { query: "memory" }), [
    "plugin-catalog",
    "-q",
    "memory",
  ]);
});

test("buildArgs explain-run and progress", () => {
  assert.deepStrictEqual(cli.buildArgs("explain-run", { runId: "run-1" }), [
    "explain-run",
    "run-1",
  ]);
  assert.deepStrictEqual(cli.buildArgs("progress"), ["progress"]);
  assert.deepStrictEqual(cli.buildArgs("v6-status"), ["v6-status"]);
});

test("buildArgs unknown throws", () => {
  assert.throws(() => cli.buildArgs("nope"), /unknown_action/);
});

test("parseCliOutput json and text", () => {
  const j = cli.parseCliOutput('{"ok":true,"x":1}');
  assert.strictEqual(j.ok, true);
  assert.strictEqual(j.json.x, 1);
  const t = cli.parseCliOutput("hello world");
  assert.strictEqual(t.text, "hello world");
  const empty = cli.parseCliOutput("  ");
  assert.strictEqual(empty.empty, true);
});

test("formatResult includes command line", () => {
  const s = cli.formatResult({
    ok: true,
    stdout: "hi",
    stderr: "",
    args: ["doctor", "--quick"],
    cliPath: "superai",
  });
  assert.ok(s.includes("$ superai doctor --quick"));
  assert.ok(s.includes("hi"));
});

test("validatePackageCommands has W7 command set", () => {
  const pkgPath = path.join(__dirname, "..", "package.json");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  const v = cli.validatePackageCommands(pkg);
  assert.strictEqual(v.ok, true, `missing: ${JSON.stringify(v.missing)}`);
  assert.ok(v.count >= v.required);
});

test("package.json version 1.x and main entry", () => {
  const pkg = JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "package.json"), "utf8")
  );
  assert.ok(pkg.version.startsWith("1."));
  assert.strictEqual(pkg.main, "./extension.js");
  assert.ok(pkg.contributes.configuration.properties["superai.cliPath"]);
  assert.ok(pkg.contributes.keybindings.length >= 1);
  assert.ok(pkg.contributes.menus["editor/context"].length >= 2);
});

test("extension.js exports activate/deactivate", () => {
  // Load without vscode: stub module cache
  const Module = require("module");
  const orig = Module.prototype.require;
  Module.prototype.require = function (id) {
    if (id === "vscode") {
      return {
        window: {
          createStatusBarItem: () => ({
            show() {},
            dispose() {},
          }),
          createOutputChannel: () => ({
            show() {},
            appendLine() {},
            dispose() {},
          }),
          showErrorMessage() {},
          showWarningMessage() {},
          showInformationMessage() {},
          setStatusBarMessage() {},
          createTerminal: () => ({ show() {}, sendText() {} }),
          showInputBox: async () => undefined,
          activeTextEditor: undefined,
        },
        workspace: {
          getConfiguration: () => ({
            get: (k) =>
              ({
                cliPath: "superai",
                timeoutMs: 1000,
                mockMode: false,
                autoShowOutput: false,
                pythonPath: "",
              })[k],
          }),
          workspaceFolders: undefined,
          openTextDocument: async () => ({}),
        },
        commands: {
          registerCommand: () => ({ dispose() {} }),
        },
        StatusBarAlignment: { Left: 1 },
      };
    }
    return orig.apply(this, arguments);
  };
  try {
    delete require.cache[require.resolve("../extension.js")];
    const ext = require("../extension.js");
    assert.strictEqual(typeof ext.activate, "function");
    assert.strictEqual(typeof ext.deactivate, "function");
    const fakeCtx = { subscriptions: [] };
    ext.activate(fakeCtx);
    assert.ok(fakeCtx.subscriptions.length >= 10);
    ext.deactivate();
  } finally {
    Module.prototype.require = orig;
    delete require.cache[require.resolve("../extension.js")];
  }
});

test("README and docs path referenced", () => {
  const readme = fs.readFileSync(path.join(__dirname, "..", "README.md"), "utf8");
  assert.ok(/W7|VS Code|SuperAI/i.test(readme));
  assert.ok(readme.length > 200);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
