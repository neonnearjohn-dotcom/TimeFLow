"""Basic environment self-check for TimeFlow."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.env_loader import load_env


REQUIRED_LIBS = {
    "aiogram": "3.4",
    "httpx": "0.27",
    "openai": "1.40",
    "google.cloud.firestore": "2.15",
}


def check_dns() -> bool:
    try:
        socket.gethostbyname("api.telegram.org")
        return True
    except Exception:
        return False


def check_env() -> list[str]:
    issues: list[str] = []
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        raw = env_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            issues.append("BOM detected in .env")
        if b"\r\n" in raw:
            issues.append("CRLF line endings in .env")
    else:
        issues.append(".env file not found")
    return issues


def check_lib_versions() -> list[str]:
    problems: list[str] = []
    for module, min_version in REQUIRED_LIBS.items():
        try:
            pkg = __import__(module)
            ver = getattr(pkg, "__version__", "0")
            if ver.split(".")[:2] < min_version.split(".")[:2]:
                problems.append(f"{module} version {ver} < {min_version}")
        except Exception as e:  # pragma: no cover - best effort
            problems.append(f"{module} import failed: {e}")
    return problems


def check_network(proxy: str | None) -> list[str]:
    if os.getenv("MOCK_MODE") == "1":
        return []
    problems: list[str] = []
    try:
        client = httpx.Client(proxy=proxy, timeout=5.0) if proxy else httpx.Client(timeout=5.0)
        resp = client.get("https://api.ipify.org")
        if resp.status_code != 200:
            problems.append("proxy test failed")
    except Exception as e:
        problems.append(f"proxy test error: {e}")
    return problems


def main() -> int:
    load_env()
    issues = []

    issues.extend(check_env())
    issues.extend(check_lib_versions())
    if not check_dns():
        issues.append("DNS resolution failed")
    issues.extend(check_network(os.getenv("OPENAI_PROXY")))

    if issues:
        print("Self-check found issues:")
        for item in issues:
            print(" -", item)
        return 1
    print("Self-check passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
