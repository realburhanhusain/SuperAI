# Code Intelligence

SuperAI includes a local source-code intelligence feature. It does not require a
separate MCP server, language server, model call, network connection, or Memory
Palace access.

## Native engine (default)

The native engine parses Python with the standard library AST. It supports graph
indexing/search, diff impact, an incremental cache, architecture summaries, and
conservative dead-code candidates.

```powershell
superai code-index --incremental
superai code-index --incremental --verify-content
superai code-index --query code_impact
superai code-impact --ref HEAD~1
superai code-report architecture
superai code-report dead-code
```

## Cache Invalidation and `--verify-content`

The code graph is cached locally (by default in `.superai/code-intelligence`) to speed up subsequent runs. The caching engine uses file signatures (size and `mtime_ns`) to rapidly verify if a file needs to be re-indexed.

If a file's content is modified but its size and modified timestamp (`mtime`) remain identical to the cached entry (e.g., spoofed via `os.utime`), the cache will assume the file is unchanged. To prevent this, use the `--verify-content` flag, which forces a SHA-256 digest comparison of the file content against the cached digest. This provides perfect cache invalidation accuracy at the cost of additional disk I/O and CPU overhead (as every file's entire content must be read and hashed).

## Advanced engine (optional)

The bundled advanced engine layers a dependency-free local scanner over the native
Python graph. It recognises JavaScript, TypeScript, Go, Java, Rust, and C# source
files as well as Python.

```powershell
superai code-report engine-status
superai code-index --engine advanced
superai code-index --engine advanced --query handler
superai code-impact --engine advanced --files src/service.ts
```

The MCP tool `superai_code_intelligence` accepts `engine: "advanced"` for `index`,
`search`, and `impact`; use `action: "engine_status"` to inspect availability.

## Accuracy and safety

The advanced engine is a conservative source scanner, not a compiler or language
server. It creates a `CALLS` edge only where a short function name resolves uniquely.
Project-local Python override chains, direct Python and TypeScript import aliases, static reflection strings, and static dynamic-module imports are resolved conservatively; computed dispatch, reflection, generated code, broad
import/package resolution, and overloaded names
can still be omitted. Treat impact and dead-code output as review evidence—not
proof—and verify before changing production code.

The incremental cache used by the native engine is stored under
`~/.superai/code-intelligence/`, outside the source repository. It records parser
settings, per-file metadata and content digests, additions, removals, renames, cache
hit rate, and elapsed time. Normal incremental runs use a fast metadata check;
`--verify-content` additionally hashes unchanged files when timestamps may be
unreliable. `superai code-report status` exposes the latest index metrics. No source
files are changed by indexing or reporting.
## Dead-code review and suppressions

`code-report dead-code` and `code-report dead-code --engine advanced` produce low-confidence review candidates only; they never remove files or symbols. For native Python reports, exclude a known indirect use with `.superai/dead-code.json`:

```json
{"exclude": ["_framework_callback", "src/plugin.py:_registered"]}
```

Use exact symbol names or `file:name` entries. Suppressions are reported in the JSON result so reviews remain auditable.
## Optional language-server providers

N235's scanners remain conservative and do not claim whole-program reachability.
Expose a provider through `PATH`, a supported user-global tool directory, or its executable override: `SUPERAI_PYTHON_LSP`, `SUPERAI_TYPESCRIPT_LSP`, `SUPERAI_GO_LSP`, `SUPERAI_RUST_LSP`, or `SUPERAI_CSHARP_LSP`. Java uses `SUPERAI_JDTLS_HOME` and optionally `SUPERAI_JAVA_EXECUTABLE`. Supported providers are basedpyright/pyright, typescript-language-server, gopls, rust-analyzer, Eclipse JDT LS, and csharp-ls.

Then run:

```powershell
superai code-report lsp-status
```

No server is installed automatically. A missing, invalid, or timed-out provider
is a non-failure with a precise reason. Dynamic imports, reflection, framework
entry points, and external callers remain outside the proof boundary, so all
findings stay advisory and source is never deleted.
Use LSP references for Python, TypeScript/JavaScript, Go, Rust, Java, and C# candidates during advanced dead-code review:

```powershell
superai code-report dead-code --engine advanced --lsp
```

The check has a bounded startup and request budget. It only removes a candidate
when the provider returns a reference beyond that symbol's declaration; an
unavailable or timed-out provider leaves the conservative candidate list intact.