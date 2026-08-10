import os
import json
import subprocess
import sys
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

def get_chrome_user_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA")) / "Google" / "Chrome" / "User Data"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    else:
        return Path.home() / ".config" / "google-chrome"

def get_chrome_binary() -> str:
    if sys.platform == "win32":
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    elif sys.platform == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:
        return "google-chrome"

def resolve_profile_dir(query: str) -> Optional[str]:
    user_data_dir = get_chrome_user_data_dir()
    local_state_path = user_data_dir / "Local State"
    if not local_state_path.exists():
        return None
        
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.warning(f"Failed to read Chrome Local State: {e}")
        return None
        
    info_cache = data.get("profile", {}).get("info_cache", {})
    query_lower = query.lower()
    
    for profile_dir, info in info_cache.items():
        email = info.get("user_name", "").lower()
        name = info.get("name", "").lower()
        if query_lower in email or query_lower in name:
            return profile_dir
            
    return None

def open_url_in_profile(url: str, profile_query: str, append_cdp_anchor: bool = True) -> bool:
    """
    Opens a URL in a specific Chrome profile resolved by email or display name.
    If append_cdp_anchor is True, appends #cdp-profile=<query> to the URL so 
    MCP tools can easily identify the tab.
    """
    profile_dir = resolve_profile_dir(profile_query)
    if not profile_dir:
        return False
        
    chrome_bin = get_chrome_binary()
    if not os.path.exists(chrome_bin) and sys.platform == "win32":
        # Fallback for 32-bit windows path
        chrome_bin = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
    if urlparse(url).scheme not in ("http", "https"):
        logging.warning(f"Invalid or unsafe URL scheme: {url}")
        return False

    target_url = url
    if append_cdp_anchor:
        target_url = f"{url}#cdp-profile={profile_query}"
        
    try:
        subprocess.Popen([
            chrome_bin,
            f"--profile-directory={profile_dir}",
            target_url
        ])
        return True
    except Exception as e:
        logging.warning(f"Failed to launch Chrome: {e}")
        return False