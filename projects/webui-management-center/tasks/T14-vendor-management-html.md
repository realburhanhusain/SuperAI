# T14 — Vendor `management.html` + manifest entry + LICENSE

| | |
|---|---|
| **Wave** | W4 |
| **Status** | `[ ]` |
| **Depends on** | **T13 (must already be committed)** |
| **Estimate** | 1.5 h |
| **Owner** | — |
| **Blocked by** | **Q3** (which commit/tag to pin), **Q4** (does `vendor_sync.py` handle HTML) |

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

1. **Resolve Q3.** Pin to a **tagged release** of
   `router-for-me/Cli-Proxy-API-Management-Center`, never `main`. Note that the
   UI's release cadence is independent of the proxy's (`v7.2.116`) — they are
   separate repos and the versions do not correspond.
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

- [ ] T13's `.gitattributes` commit is already an ancestor (`git merge-base --is-ancestor`).
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
