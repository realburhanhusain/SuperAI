"""
GitHub product API helpers (G15) — issues & PRs.

Uses GITHUB_TOKEN / GH_TOKEN for REST API when set.
Falls back to `gh` CLI when on PATH.
Dry-run / offline stubs when neither is available.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def _token() -> str:
    return (
        (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("SUPERAI_GITHUB_TOKEN") or "")
        .strip()
    )


def _gh_cli() -> Optional[str]:
    return shutil.which("gh") or shutil.which("gh.exe")


def _api(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    token = _token()
    url = f"https://api.github.com{path}"
    if dry_run or not token:
        return {
            "ok": True,
            "dry_run": True,
            "method": method,
            "url": url,
            "body": body,
            "note": "Set GITHUB_TOKEN for live API, or use gh CLI.",
        }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SuperAI-github-api",
            **({"Content-Type": "application/json"} if data else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw.strip() else {}
            return {"ok": True, "status": resp.status, "data": parsed}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:800]
        return {"ok": False, "status": e.code, "error": err_body or str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def _gh_json(args: List[str], dry_run: bool = False) -> Dict[str, Any]:
    exe = _gh_cli()
    if not exe:
        return {"ok": False, "error": "gh CLI not on PATH"}
    if dry_run:
        return {"ok": True, "dry_run": True, "command": [exe, *args]}
    try:
        proc = subprocess.run(
            [exe, *args],
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        out = (proc.stdout or "").strip()
        data = json.loads(out) if out.startswith(("{", "[")) else {"raw": out}
        return {
            "ok": proc.returncode == 0,
            "data": data,
            "stderr": (proc.stderr or "")[:500],
            "exit_code": proc.returncode,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def parse_repo(repo: Optional[str] = None) -> str:
    """owner/name — from arg, SUPERAI_GITHUB_REPO, or gh repo view."""
    if repo and "/" in repo:
        return repo.strip()
    env = (os.getenv("SUPERAI_GITHUB_REPO") or "").strip()
    if env and "/" in env:
        return env
    # try gh
    r = _gh_json(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if r.get("ok") and isinstance(r.get("data"), str) and "/" in r["data"]:
        return r["data"]
    if r.get("ok") and isinstance(r.get("data"), dict):
        n = r["data"].get("nameWithOwner")
        if n:
            return str(n)
    return ""


class GitHubClient:
    def __init__(self, repo: Optional[str] = None, dry_run: Optional[bool] = None):
        if dry_run is None:
            dry_run = (os.getenv("SUPERAI_GITHUB_DRY_RUN") or "").lower() in {
                "1",
                "true",
                "yes",
            }
        self.dry_run = dry_run
        self.repo = parse_repo(repo)

    def status(self) -> Dict[str, Any]:
        return {
            "repo": self.repo or None,
            "token_set": bool(_token()),
            "gh_cli": _gh_cli(),
            "dry_run": self.dry_run,
            "can_live": bool(_token() or _gh_cli()) and not self.dry_run,
        }

    def list_issues(
        self,
        state: str = "open",
        limit: int = 20,
    ) -> Dict[str, Any]:
        if not self.repo:
            return {"ok": False, "error": "repo required (owner/name or SUPERAI_GITHUB_REPO)"}
        # Prefer REST when token
        if _token() and not self.dry_run:
            q = urllib.parse.urlencode({"state": state, "per_page": str(min(limit, 50))})
            r = _api("GET", f"/repos/{self.repo}/issues?{q}", dry_run=False)
            if not r.get("ok"):
                return r
            items = []
            for it in r.get("data") or []:
                if it.get("pull_request"):
                    continue  # issues endpoint includes PRs
                items.append(
                    {
                        "number": it.get("number"),
                        "title": it.get("title"),
                        "state": it.get("state"),
                        "url": it.get("html_url"),
                        "user": (it.get("user") or {}).get("login"),
                    }
                )
            return {"ok": True, "repo": self.repo, "issues": items[:limit], "via": "api"}
        # gh CLI
        if _gh_cli():
            r = _gh_json(
                [
                    "issue",
                    "list",
                    "--repo",
                    self.repo,
                    "--state",
                    state,
                    "--limit",
                    str(limit),
                    "--json",
                    "number,title,state,url,author",
                ],
                dry_run=self.dry_run,
            )
            if r.get("dry_run"):
                return {**r, "repo": self.repo}
            if not r.get("ok"):
                return r
            data = r.get("data") or []
            if isinstance(data, list):
                issues = [
                    {
                        "number": i.get("number"),
                        "title": i.get("title"),
                        "state": i.get("state"),
                        "url": i.get("url"),
                        "user": (i.get("author") or {}).get("login"),
                    }
                    for i in data
                ]
                return {"ok": True, "repo": self.repo, "issues": issues, "via": "gh"}
        return {
            "ok": True,
            "dry_run": True,
            "repo": self.repo,
            "issues": [],
            "note": "No GITHUB_TOKEN or gh — offline stub",
        }

    def create_issue(
        self,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not self.repo:
            return {"ok": False, "error": "repo required"}
        if not title.strip():
            return {"ok": False, "error": "title required"}
        payload = {"title": title, "body": body or ""}
        if labels:
            payload["labels"] = labels
        if _token():
            r = _api(
                "POST",
                f"/repos/{self.repo}/issues",
                body=payload,
                dry_run=self.dry_run,
            )
            if r.get("dry_run"):
                return r
            if r.get("ok"):
                d = r.get("data") or {}
                return {
                    "ok": True,
                    "number": d.get("number"),
                    "url": d.get("html_url"),
                    "via": "api",
                }
            return r
        if _gh_cli():
            args = [
                "issue",
                "create",
                "--repo",
                self.repo,
                "--title",
                title,
                "--body",
                body or " ",
            ]
            for lb in labels or []:
                args.extend(["--label", lb])
            if self.dry_run:
                return {"ok": True, "dry_run": True, "command": ["gh", *args[0:]]}
            try:
                proc = subprocess.run(
                    [_gh_cli() or "gh", *args],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    shell=False,
                )
                return {
                    "ok": proc.returncode == 0,
                    "url": (proc.stdout or "").strip(),
                    "stderr": (proc.stderr or "")[:400],
                    "via": "gh",
                }
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": str(e)}
        return {
            "ok": True,
            "dry_run": True,
            "title": title,
            "body": body,
            "note": "Would create issue — set GITHUB_TOKEN or install gh",
        }

    def list_prs(
        self,
        state: str = "open",
        limit: int = 20,
    ) -> Dict[str, Any]:
        if not self.repo:
            return {"ok": False, "error": "repo required"}
        if _token() and not self.dry_run:
            q = urllib.parse.urlencode({"state": state, "per_page": str(min(limit, 50))})
            r = _api("GET", f"/repos/{self.repo}/pulls?{q}")
            if not r.get("ok"):
                return r
            items = [
                {
                    "number": it.get("number"),
                    "title": it.get("title"),
                    "state": it.get("state"),
                    "url": it.get("html_url"),
                    "user": (it.get("user") or {}).get("login"),
                    "draft": it.get("draft"),
                }
                for it in (r.get("data") or [])
            ]
            return {"ok": True, "repo": self.repo, "pulls": items[:limit], "via": "api"}
        if _gh_cli():
            r = _gh_json(
                [
                    "pr",
                    "list",
                    "--repo",
                    self.repo,
                    "--state",
                    state,
                    "--limit",
                    str(limit),
                    "--json",
                    "number,title,state,url,author,isDraft",
                ],
                dry_run=self.dry_run,
            )
            if r.get("dry_run"):
                return {**r, "repo": self.repo}
            if not r.get("ok"):
                return r
            data = r.get("data") or []
            if isinstance(data, list):
                pulls = [
                    {
                        "number": i.get("number"),
                        "title": i.get("title"),
                        "state": i.get("state"),
                        "url": i.get("url"),
                        "user": (i.get("author") or {}).get("login"),
                        "draft": i.get("isDraft"),
                    }
                    for i in data
                ]
                return {"ok": True, "repo": self.repo, "pulls": pulls, "via": "gh"}
        return {
            "ok": True,
            "dry_run": True,
            "repo": self.repo,
            "pulls": [],
            "note": "No GITHUB_TOKEN or gh — offline stub",
        }

    def get_pr(self, number: int) -> Dict[str, Any]:
        if not self.repo:
            return {"ok": False, "error": "repo required"}
        if _token() and not self.dry_run:
            r = _api("GET", f"/repos/{self.repo}/pulls/{int(number)}")
            if not r.get("ok"):
                return r
            d = r.get("data") or {}
            return {
                "ok": True,
                "number": d.get("number"),
                "title": d.get("title"),
                "body": (d.get("body") or "")[:4000],
                "state": d.get("state"),
                "url": d.get("html_url"),
                "mergeable": d.get("mergeable"),
                "via": "api",
            }
        if _gh_cli():
            r = _gh_json(
                [
                    "pr",
                    "view",
                    str(number),
                    "--repo",
                    self.repo,
                    "--json",
                    "number,title,body,state,url,mergeable",
                ],
                dry_run=self.dry_run,
            )
            if r.get("dry_run"):
                return r
            return {"ok": r.get("ok"), "data": r.get("data"), "via": "gh", **(
                r.get("data") if isinstance(r.get("data"), dict) else {}
            )}
        return {
            "ok": True,
            "dry_run": True,
            "number": number,
            "note": "Would fetch PR — set GITHUB_TOKEN or install gh",
        }

    def comment_on_issue(self, number: int, body: str) -> Dict[str, Any]:
        if not self.repo:
            return {"ok": False, "error": "repo required"}
        if _token():
            return _api(
                "POST",
                f"/repos/{self.repo}/issues/{int(number)}/comments",
                body={"body": body},
                dry_run=self.dry_run,
            )
        if _gh_cli() and not self.dry_run:
            try:
                proc = subprocess.run(
                    [
                        _gh_cli() or "gh",
                        "issue",
                        "comment",
                        str(number),
                        "--repo",
                        self.repo,
                        "--body",
                        body,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    shell=False,
                )
                return {
                    "ok": proc.returncode == 0,
                    "stdout": (proc.stdout or "")[:300],
                    "via": "gh",
                }
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": str(e)}
        return {
            "ok": True,
            "dry_run": True,
            "number": number,
            "body": body[:500],
            "note": "Would comment — set GITHUB_TOKEN or install gh",
        }
