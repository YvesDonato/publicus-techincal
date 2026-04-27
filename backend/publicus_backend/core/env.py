from __future__ import annotations

import os
import re
from pathlib import Path


ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_root_env() -> None:
    env_path = find_root_env()
    if env_path is None:
        return

    for key, value in read_env_file(env_path).items():
        os.environ.setdefault(key, value)


def find_root_env() -> Path | None:
    current_file = Path(__file__).resolve()
    for parent in current_file.parents:
        if (parent / "flake.nix").is_file():
            candidate = parent / ".env"
            return candidate if candidate.is_file() else None

    return None


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_env_line(raw_line)
        if parsed is None:
            continue

        key, value = parsed
        values[key] = value

    return values


def parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("export "):
        line = line.removeprefix("export ").strip()

    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    if not ENV_KEY_RE.match(key):
        return None

    return key, parse_env_value(value.strip())


def parse_env_value(value: str) -> str:
    if not value:
        return ""

    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]

    return value.split(" #", 1)[0].strip()
