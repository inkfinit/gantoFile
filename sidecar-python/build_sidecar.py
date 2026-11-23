"""Automated PyInstaller build script for Ganto Tauri sidecar binaries."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def detect_target_triple() -> str:
    """Detect the Rust/Tauri target triple for the current host machine."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        if machine in ("x86_64", "amd64"):
            return "x86_64-apple-darwin"
    elif system == "windows":
        if machine in ("amd64", "x86_64", "x64"):
            return "x86_64-pc-windows-msvc"
        if machine in ("arm64", "aarch64"):
            return "aarch64-pc-windows-msvc"
    elif system == "linux":
        if machine in ("x86_64", "amd64"):
            return "x86_64-unknown-linux-gnu"
        if machine in ("aarch64", "arm64"):
            return "aarch64-unknown-linux-gnu"

    raise RuntimeError(f"Unsupported host platform: {system} / {machine}")


def main() -> None:
    """Compile engine.py with PyInstaller and install into src-tauri/binaries."""
    parser = argparse.ArgumentParser(description="Build Ganto sidecar binary via PyInstaller")
    parser.add_argument(
        "--target",
        default=None,
        help="Target triple override (e.g. aarch64-apple-darwin, x86_64-pc-windows-msvc)",
    )
    args = parser.parse_args()

    target_triple = args.target or detect_target_triple()
    sidecar_dir = Path(__file__).resolve().parent
    project_root = sidecar_dir.parent
    binaries_dir = project_root / "src-tauri" / "binaries"
    binaries_dir.mkdir(parents=True, exist_ok=True)

    is_windows = "windows" in target_triple
    base_name = "ganto-engine"
    built_exe = sidecar_dir / "dist" / (f"{base_name}.exe" if is_windows else base_name)
    dest_name = f"{base_name}-{target_triple}.exe" if is_windows else f"{base_name}-{target_triple}"
    dest_path = binaries_dir / dest_name

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--name",
        base_name,
        "--paths",
        str(sidecar_dir),
        "--hidden-import",
        "cleaner",
        "--hidden-import",
        "fitz",
        "--hidden-import",
        "pdf2docx",
        "--hidden-import",
        "docx",
        "--collect-all",
        "pdf2docx",
        "--collect-all",
        "docx",
        str(sidecar_dir / "engine.py"),
    ]

    print(f"Building sidecar for {target_triple} using {sys.executable}...")
    env = os.environ.copy()
    env.setdefault("PYINSTALLER_CONFIG_DIR", str(sidecar_dir / "build" / ".pyinstaller"))
    subprocess.run(cmd, cwd=str(sidecar_dir), env=env, check=True)

    if not built_exe.exists():
        raise FileNotFoundError(f"Expected PyInstaller output not found: {built_exe}")

    shutil.copy2(built_exe, dest_path)
    if not is_windows:
        os.chmod(dest_path, 0o755)

    print(f"Installed sidecar binary: {dest_path}")


if __name__ == "__main__":
    main()
