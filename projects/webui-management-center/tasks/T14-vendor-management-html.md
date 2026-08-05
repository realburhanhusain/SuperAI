# T14 — Vendor `management.html` + manifest entry + LICENSE

| | |
|---|---|
| **Wave** | W4 |
| **Status** | `[ ]` |
| **Depends on** | **T13 (verification must have passed)** |
| **Estimate** | 1.5 h |
| **Owner** | — |
| **Blocked by** | **Q4** (does `vendor_sync.py` handle HTML). Q3 answered — see below. |

## Q3 — answered (2026-08-05)

**Pin the Management Center to its own separate tag.** It is a distinct repo
with a release cadence independent of CLIProxyAPI's, so its version does **not**
correspond to the proxy's `v7.2.116`. Record it as its own manifest entry with
its own ref; do not derive, infer, or align it with the proxy's pin. Never
`main`.

## T13 note

T13 shrank to a verification step — `vendor/.gitattributes` already carries
`* -text` recursively, so `vendor/mgmt-ui/` is covered with no new file needed.
Run T13's two checks and confirm they pass **before** committing bytes here.

## Goal

Bring the Management Center's prebuilt single-file UI into `vendor/` under this
repo's existing pinning discipline — unmodified, byte-exact, attributed.

## This is a deliberate policy change, not a routine addition

`vendor/manifest.json:68-78` currently records `cliproxy` as a
**`pinned_reference`** — a citation with *no bytes*, justified explicitly:
"SuperAI speaks its OpenAI-compatible protocol over HTTP and reads none of its
source, so nothing is vendored."

Vendoring `management.html` changes that. It is a **new kind** of dependency on
that project's ecosystem: bytes we ship. Add it as a distinct `vendored_files`
entry and say so plainly in the manifest note. Do not quietly mutate the
existing `pinned_reference` row as if nothing changed — the next reader should
be able to see that the relationship changed and when.

Read `vendor/README.md:12-24` for the distinction between the two kinds before
writing the entry.

## Steps

1. Pick the **tagged release** of `router-for-me/Cli-Proxy-API-Management-Center`
   to pin (Q3: its own separate tag — see above). Never `main`.
2. Obtain `dist/index.html` for that exact tag. Options, in order of preference:
   - a release asset for the tag;
   - the `management.html` shipped inside a pinned CLIProxyAPI release ≥ 6.0.19;
   - building from the pinned source with Bun **outside this repo**, never
     introducing the toolchain here (constraint C7).
   Record in the Log **which** you used — provenance is the point of the pin.
3. Place at `vendor/mgmt-ui/management.html`. **Do not edit it.** Any local
   modification breaks both the sha256 pin and the "unmodified upstream" claim
   that makes this safe to update later.
4. Copy the upstream MIT `LICENSE` alongside it as
   `vendor/mgmt-ui/LICENSE`, with a `NOTICE` naming the project, the pinned
   ref, and the source URL. MIT permits redistribution of the built artifact
   **provided attribution travels with it** — this is that attribution.
5. Add a `vendored_files` entry to `vendor/manifest.json`: exact commit/tag,
   sha256 of the file, license `MIT`, and a one-line note on why bytes are
   vendored here when the proxy itself is reference-only.
6. **Resolve Q4:** check whether `scripts/vendor_sync.py --check` generalizes to
   an HTML entry. If not, extend it — an entry the integrity checker skips is
   worse than no entry, because the manifest then implies a verification that
   never runs.

## Acceptance criteria

- [ ] T13's two verification checks ran and passed **before** these bytes were committed (`git check-attr` → `text: unset`; `vendor_sync --check` → all pinned files match).
- [ ] `vendor/mgmt-ui/management.html` present, byte-identical to upstream, sha256 recorded in the manifest.
- [ ] `LICENSE` + `NOTICE` present with the pinned ref and source URL.
- [ ] Manifest entry is `vendored_files`, pinned to a **tag or commit**, never a branch.
- [ ] `python scripts/vendor_sync.py --check` passes **and actually checks this entry** — prove it by corrupting one byte locally and confirming the check *fails*, then restoring.
- [ ] A fresh `git clone` of the branch yields a file whose sha256 still matches (catches the CRLF trap T13 guards).

## Verification command

```powershell
python scripts/vendor_sync.py --check
# prove the check is real, not vacuous:
#   corrupt one byte -> re-run -> must FAIL -> restore -> must PASS
```

## Log

_(record Q3/Q4 answers, the artifact's provenance, and the corrupt-byte proof before marking `[x]`)_
