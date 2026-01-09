#!/usr/bin/env python3
"""
Generate PAN-OS API keys for Baker Street Labs cyber range firewalls.

Usage:
    python generate_firewall_api_keys.py --username admin --password <PASSWORD>

The script will:
  * Request API keys from each firewall using the XML API keygen endpoint.
  * Write the resulting keys to ~/.secrets (or a provided secrets path).
  * Avoid printing full API keys; output is truncated for safety.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

from panos_api import (
    SecretsError,
    firewall_ids,
    iter_firewalls,
    request_api_key,
    update_secrets,
)


def mask_key(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and store PAN-OS API keys in ~/.secrets.",
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Firewall administrator username.",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Firewall administrator password.",
    )
    parser.add_argument(
        "--firewall",
        choices=firewall_ids(),
        help="Generate a key for a single firewall (default: all).",
    )
    parser.add_argument(
        "--secrets-path",
        type=Path,
        default=Path.home() / ".secrets",
        help="Path to the secrets file (default: ~/.secrets).",
    )

    args = parser.parse_args()

    secrets_path: Path = args.secrets_path
    secrets_path.parent.mkdir(parents=True, exist_ok=True)

    updates: Dict[str, str] = {}

    for firewall in iter_firewalls(args.firewall):
        print(f"[*] Requesting API key from {firewall.name} ({firewall.hostname})...")
        try:
            api_key = request_api_key(firewall, args.username, args.password)
        except SecretsError as exc:
            print(f"[ERROR] {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] Unexpected failure for {firewall.name}: {exc}")
            continue

        key_name = f"{firewall.name.upper()}_API_KEY"
        updates[key_name] = api_key
        print(f"[OK] Retrieved API key for {firewall.name}: {mask_key(api_key)}")

    if not updates:
        print("[WARN] No API keys were generated.")
        return

    update_secrets(secrets_path, updates)
    print(f"[SUCCESS] Updated {secrets_path} with {len(updates)} API key(s).")


if __name__ == "__main__":
    main()


