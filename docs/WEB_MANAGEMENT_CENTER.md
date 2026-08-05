# Web Management Center (optional)

SuperAI provides a browser-based UI for configuration editing and runtime status monitoring. This feature is split into two parts:

1. **SuperAI-native pages and endpoints** added to the existing FastAPI app for managing internal SuperAI config.
2. **An embedded console for a *separate* proxy.** The MIT-licensed [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI/tree/v7.2.116) Management Center (`management.html`) is vendored and served at `/cliproxy-admin`.

**The Management Center manages CLIProxyAPI, not SuperAI.** It serves as an operator console for the separate, optional CLIProxyAPI process.

**This feature is entirely additive and opt-in.** By default, `superai web` operates normally with no write access. Nothing was removed.

## Enabling it

Every capability of the Management Center is turned off by default. You enable them selectively using environment variables:

| Environment Variable | Purpose | Default |
|---|---|---|
| `SUPERAI_WEB_TOKEN` | Secures general read-only endpoints (e.g., `/console`, `/api/spend`). | Off (no auth required) |
| `SUPERAI_WEB_MANAGEMENT_TOKEN` | Gates all write endpoints and the `/api/audit` log. Required for *any* configuration changes. | Off (writes disabled) |
| `SUPERAI_WEB_ENABLE_CONFIG_WRITE` | Flag to register `POST /api/config`, `POST /api/models`, and rollback endpoints. Must be `1` to allow modifying config. | `0` (off) |
| `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN` | Flag to mount the vendored CLIProxyAPI Management Center at `/cliproxy-admin`. | `0` (off) |

To fully enable the Management Center:
```powershell
$env:SUPERAI_WEB_MANAGEMENT_TOKEN = "your-secret-token"
$env:SUPERAI_WEB_ENABLE_CONFIG_WRITE = "1"
$env:SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN = "1"
superai web
```

## Endpoint reference

| Endpoint | Action | Requires |
|---|---|---|
| `GET /console` | Aggregated read-only status dashboard | `SUPERAI_WEB_TOKEN` (if set) |
| `GET /api/spend`, `/api/goals`, `/api/cliproxy/status` | Read-only metrics and status | `SUPERAI_WEB_TOKEN` (if set) |
| `GET /api/config/diff` | Preview config changes without applying | `SUPERAI_WEB_MANAGEMENT_TOKEN` |
| `GET /api/audit` | Read the audit log | `SUPERAI_WEB_MANAGEMENT_TOKEN` |
| `GET /cliproxy-admin` | Vendored Management Center UI | `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN=1` |
| `POST /api/config`, `POST /api/models` | Apply atomic config changes | `SUPERAI_WEB_MANAGEMENT_TOKEN` & `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1` |
| `POST /api/config/rollback` | Revert to a backup snapshot | `SUPERAI_WEB_MANAGEMENT_TOKEN` & `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1` |

## Config-write semantics

When you edit configuration in the browser via `/api/config` or `/api/models`:

1. **Writes never touch repo-tracked files.** Modifications target `~/.superai/config.json` and `~/.superai/config/models.json` exclusively. These override repo defaults due to the precedence rule.
2. **Validation & Diffing.** You can request a dry-run diff (`GET /api/config/diff` or `POST` equivalent) which validates the payload against internal schemas.
3. **Atomic writes.** Saving configuration is fully atomic. A temporary file is written, fsync'd, and then `os.replace` is used to prevent any partial or corrupted states if the process dies.
4. **Automatic backups.** Before any successful write, the previous configuration is snapshotted into `~/.superai/backups/`.
5. **Rollback.** `POST /api/config/rollback` can restore an exact backup state safely, and it also takes a backup *before* rolling back to ensure you never lose data.

## Hot reload

Not all configuration applies immediately. SuperAI instantiates certain settings once at startup. 
As demonstrated in T06 and T09, **if you modify database paths or global API keys, you must restart the `superai web` process.** 
Settings are pushed down into the `cfg` singleton in `src/core/config.py`, but downstream clients that hold a static reference (such as connection pools) will not pick up the change dynamically until a restart.

## Security

*   **Management Token.** The `SUPERAI_WEB_MANAGEMENT_TOKEN` is separate from the base read token. Loopback requests (from `127.0.0.1`) are intentionally *not* trusted for writes; you must always provide the management token in the HTTP header for mutation routes.
*   **Storage.** The UI uses `sessionStorage` strictly. It never writes the management token into `localStorage` where it might persist indefinitely across sessions.
*   **CSRF-safe.** The design is CSRF-safe by construction because the token is placed in an `Authorization: Bearer` header, not a cookie. A malicious page cannot forge this request because it cannot read your token to inject the header. **This property only holds if the token is never moved into a cookie.**
*   **Audit Logging.** All mutation operations (successes and validation failures) are logged to the `~/.superai/` directory and surfaced natively via `GET /api/audit`.

## A caution worth stating

Wrapping *subscription* access as a general-purpose API may conflict with those vendors' terms of service. Popularity is not sanction, and 46k stars is not a legal opinion. That matters more for work-related use than personal use. This integration is opt-in specifically so the choice stays deliberate.

## Vendoring

The CLIProxyAPI Management Center UI is shipped statically within SuperAI.
- The UI is pinned exactly to tag `v1.21.4` (the `management.html` release asset).
- The file and its MIT LICENSE are stored in `vendor/mgmt-ui/`.
- The exact sha256 hashes are recorded in `vendor/manifest.json`.
- A `.gitattributes` file protects `vendor/` from CRLF conversion (`* -text`), which is critical to ensure `vendor_sync.py` hash checks pass across all OS environments without silent byte modification.
