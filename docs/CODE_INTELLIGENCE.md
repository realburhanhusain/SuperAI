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
Dynamic dispatch, reflection, generated code, imports/aliases, and overloaded names
can therefore be omitted. Treat impact and dead-code output as review evidence—not
proof—and verify before changing production code.

The incremental cache used by the native engine is stored under
`~/.superai/code-intelligence/`, outside the source repository. It records parser
settings, per-file metadata and content digests, additions, removals, renames, cache
hit rate, and elapsed time. Normal incremental runs use a fast metadata check;
`--verify-content` additionally hashes unchanged files when timestamps may be
unreliable. `superai code-report status` exposes the latest index metrics. No source
files are changed by indexing or reporting.