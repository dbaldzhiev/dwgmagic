"""Update checking against GitHub releases.

Deliberately dependency-free (urllib + stdlib json) and network-tolerant:
every failure path returns ``None`` so an offline machine never sees an
error because of the update check.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from packaging.version import InvalidVersion, Version

import dwgmagic
from dwgmagic.settings import APP_ROOT, GITHUB_REPO

_API_TIMEOUT = 6.0


@dataclass(slots=True)
class UpdateInfo:
    current: str
    latest: str
    url: str
    notes: str


def _parse_version(raw: str) -> Optional[Version]:
    try:
        return Version(raw.lstrip("vV"))
    except InvalidVersion:
        return None


def fetch_latest_release(repo: str = GITHUB_REPO) -> Optional[dict]:
    """Return the GitHub 'latest release' payload, or None on any failure."""

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"dwgmagic/{dwgmagic.__version__}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=_API_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - offline/ratelimit/404 all mean "no update info"
        return None


def check_for_update(repo: str = GITHUB_REPO) -> Optional[UpdateInfo]:
    """Compare the installed version against the latest GitHub release."""

    payload = fetch_latest_release(repo)
    if not payload:
        return None

    latest_raw = str(payload.get("tag_name") or "")
    latest = _parse_version(latest_raw)
    current = _parse_version(dwgmagic.__version__)
    if latest is None or current is None or latest <= current:
        return None

    return UpdateInfo(
        current=str(current),
        latest=str(latest),
        url=str(payload.get("html_url") or f"https://github.com/{repo}/releases"),
        notes=str(payload.get("body") or "").strip(),
    )


def updater_script() -> Optional[Path]:
    """Path to the on-disk updater, if this copy of the app ships one."""

    script = APP_ROOT / "update.bat"
    return script if script.exists() else None


def launch_updater(relaunch_gui: bool = True) -> bool:
    """Start the detached updater script; returns False if unavailable.

    The caller should exit promptly afterwards so the updater can replace
    the application files.
    """

    script = updater_script()
    if script is None:
        return False
    args = [str(script)]
    if relaunch_gui:
        args.append("/relaunch")
    creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(  # noqa: S603 - launching our own updater
        args,
        cwd=str(APP_ROOT),
        creationflags=creation_flags,
        close_fds=True,
    )
    return True


__all__ = ["UpdateInfo", "check_for_update", "fetch_latest_release", "launch_updater"]
