#!/usr/bin/env python3
"""Manage optional ARPANET logs volume setup and retention cleanup."""

from __future__ import annotations

import argparse
import json
import os
import pwd
import grp
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def _coerce_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _all_disks() -> list[str]:
    proc = _run(["lsblk", "-J", "-o", "PATH,TYPE"])  # nosec B603
    payload = json.loads(proc.stdout)

    disks: list[str] = []

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            if node.get("type") == "disk" and node.get("path"):
                disks.append(str(node["path"]))
            children = node.get("children") or []
            if children:
                walk(children)

    walk(payload.get("blockdevices", []))
    return sorted(set(disks))


def _root_disk() -> str | None:
    src = _run(["findmnt", "-n", "-o", "SOURCE", "/"]).stdout.strip()  # nosec B603
    if not src:
        return None
    pk = _run(["lsblk", "-n", "-o", "PKNAME", src], check=False).stdout.strip()  # nosec B603
    if pk:
        return f"/dev/{pk}"
    return src


def _discover_logs_device(label: str) -> str | None:
    labeled = _run(["blkid", "-L", label], check=False).stdout.strip()  # nosec B603
    if labeled:
        return labeled

    root_disk = _root_disk()
    candidates = [d for d in _all_disks() if d != root_disk]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    for preferred in ("/dev/nvme1n1", "/dev/xvdf", "/dev/sdf"):
        if preferred in candidates:
            return preferred

    print(
        "WARNING: multiple candidate non-root disks found; "
        f"using first sorted candidate: {candidates[0]}",
        file=sys.stderr,
    )
    return candidates[0]


def _ensure_filesystem(device: str, label: str) -> None:
    has_fs = _run(["blkid", device], check=False).returncode == 0  # nosec B603
    if has_fs:
        print(f"Filesystem already present on {device}")
        return
    print(f"Formatting {device} as ext4 with label {label}")
    _run(["mkfs.ext4", "-L", label, device])  # nosec B603


def _ensure_mount(label: str, device: str, mount_point: Path) -> None:
    mount_point.mkdir(parents=True, exist_ok=True)
    mounted = _run(["findmnt", "-n", str(mount_point)], check=False).returncode == 0  # nosec B603
    if not mounted:
        print(f"Mounting {device} at {mount_point}")
        _run(["mount", device, str(mount_point)])  # nosec B603

    fstab_line = f"LABEL={label} {mount_point} ext4 defaults,nofail 0 2"
    with Path("/etc/fstab").open("r", encoding="utf-8") as f:
        existing = f.read()
    if fstab_line not in existing:
        with Path("/etc/fstab").open("a", encoding="utf-8") as f:
            f.write(f"\n{fstab_line}\n")


def _chown_path(path: Path, user: str = "ubuntu", group: str = "ubuntu") -> None:
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    os.chown(path, uid, gid)


def _ensure_log_dirs(mount_point: Path) -> None:
    for rel in ("builds", "active"):
        p = mount_point / rel
        p.mkdir(parents=True, exist_ok=True)
        _chown_path(p)
    _chown_path(mount_point)


def _cleanup_old_entries(base_dir: Path, retention_days: int) -> int:
    if not base_dir.exists():
        return 0
    cutoff = time.time() - (retention_days * 24 * 60 * 60)
    deleted = 0
    for child in base_dir.iterdir():
        try:
            if child.stat().st_mtime >= cutoff:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
            deleted += 1
        except FileNotFoundError:
            continue
    return deleted


def _run_cleanup(mount_point: Path, retention_days: int) -> None:
    removed = 0
    for rel in ("builds", "active"):
        removed += _cleanup_old_entries(mount_point / rel, retention_days)
    print(f"Retention cleanup complete (removed {removed} entries older than {retention_days} days)")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["setup", "cleanup"], default="setup")
    parser.add_argument("--logs-enabled", default="true")
    parser.add_argument("--retention-days", type=int, default=14)
    parser.add_argument("--mount-point", default="/mnt/arpanet-logs")
    parser.add_argument("--label", default="arpanet-logs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    logs_enabled = _coerce_bool(str(args.logs_enabled))
    mount_point = Path(args.mount_point)

    if args.retention_days < 1:
        print("retention-days must be >= 1", file=sys.stderr)
        return 2

    if args.mode == "cleanup":
        _run_cleanup(mount_point, args.retention_days)
        return 0

    if not logs_enabled:
        print("Persistent logs volume disabled; ensuring local log directories only")
        _ensure_log_dirs(mount_point)
        _run_cleanup(mount_point, args.retention_days)
        return 0

    device = _discover_logs_device(args.label)
    if not device:
        print("No non-root logs device found while logs volume is enabled", file=sys.stderr)
        return 1

    print(f"Using logs device: {device}")
    _ensure_filesystem(device, args.label)
    _ensure_mount(args.label, device, mount_point)
    _ensure_log_dirs(mount_point)
    _run_cleanup(mount_point, args.retention_days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
