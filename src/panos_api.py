#!/usr/bin/env python3
"""
Shared PAN-OS XML API helpers for Baker Street Labs tooling.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import xml.etree.ElementTree as ET

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_TIMEOUT = 30
RULEBASE_XPATH = (
    "/config/devices/entry[@name='localhost.localdomain']"
    "/vsys/entry[@name='vsys1']/rulebase/security"
)


@dataclass(frozen=True)
class Firewall:
    name: str
    hostname: str
    description: str


FIREWALLS: Dict[str, Firewall] = {
    "rangeagentix": Firewall(
        name="rangeagentix",
        hostname="rangeagentix.bakerstreetlabs.io",
        description="Range Agentix firewall",
    ),
    "rangexdr": Firewall(
        name="rangexdr",
        hostname="rangexdr.bakerstreetlabs.io",
        description="Range XDR baseline firewall",
    ),
    "rangexsiam": Firewall(
        name="rangexsiam",
        hostname="rangexsiam.bakerstreetlabs.io",
        description="Range XSIAM firewall",
    ),
    "rangeplatform": Firewall(
        name="rangeplatform",
        hostname="rangeplatform.bakerstreetlabs.io",
        description="Range Platform firewall",
    ),
}


class SecretsError(RuntimeError):
    """Raised when required secrets are missing or invalid."""


def firewall_ids() -> List[str]:
    return sorted(FIREWALLS.keys())


def iter_firewalls(name: Optional[str] = None) -> Iterable[Firewall]:
    if name:
        firewall = FIREWALLS.get(name)
        if firewall is None:
            raise KeyError(f"Unknown firewall '{name}'. Valid options: {', '.join(firewall_ids())}")
        return [firewall]
    return FIREWALLS.values()


def load_secrets(path: Optional[Path] = None) -> Dict[str, str]:
    secrets_path = path or Path.home() / ".secrets"
    if not secrets_path.exists():
        raise SecretsError(f"Secrets file not found at {secrets_path}.")

    secrets: Dict[str, str] = {}

    for raw_line in secrets_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        secrets[key.strip()] = value.strip()

    if not secrets:
        raise SecretsError(f"No credentials found in {secrets_path}.")

    return secrets


def update_secrets(path: Path, updates: Dict[str, str]) -> None:
    """Update key=value pairs in the secrets file, preserving existing content."""
    if not path.exists():
        path.touch()

    lines = path.read_text(encoding="utf-8").splitlines()
    output_lines: List[str] = []
    updated_keys: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                output_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        output_lines.append(line)

    for key, value in updates.items():
        if key in updated_keys:
            continue
        if output_lines and output_lines[-1].strip():
            output_lines.append("")
        output_lines.append(f"{key}={value}")

    if output_lines and output_lines[-1] != "":
        output_lines.append("")

    path.write_text("\n".join(output_lines), encoding="utf-8")


def request_api_key(firewall: Firewall, username: str, password: str) -> str:
    response = requests.get(
        f"https://{firewall.hostname}/api/",
        params={
            "type": "keygen",
            "user": username,
            "password": password,
        },
        verify=False,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    if root.get("status") != "success":
        error_msg = root.findtext(".//msg")
        raise SecretsError(
            f"Keygen failed for {firewall.name}: {error_msg or 'Unknown error'}"
        )

    key_value = root.findtext(".//key")
    if not key_value:
        raise SecretsError(f"Keygen response missing API key for {firewall.name}.")
    return key_value


def resolve_api_key(firewall: Firewall, secrets: Dict[str, str]) -> str:
    candidate_keys = [
        secrets.get(f"{firewall.name.upper()}_API_KEY"),
        secrets.get("PANOS_API_KEY"),
    ]

    for candidate in candidate_keys:
        if candidate:
            return candidate

    username = secrets.get("PANOS_USERNAME")
    password = secrets.get("PANOS_PASSWORD")
    if username and password:
        return request_api_key(firewall, username, password)

    raise SecretsError(
        "No API key available. Provide either PANOS_API_KEY, "
        f"{firewall.name.upper()}_API_KEY, or PANOS_USERNAME/PANOS_PASSWORD."
    )


def fetch_security_rules(firewall: Firewall, api_key: str) -> ET.Element:
    root = api_call(
        firewall,
        api_key,
        params={
            "type": "config",
            "action": "show",
            "xpath": RULEBASE_XPATH,
        },
    )
    return root


def call_with_handling(func, *args, **kwargs):
    """Helper to wrap API calls with consistent exception handling."""
    try:
        return func(*args, **kwargs)
    except (requests.RequestException, ssl.SSLError) as exc:
        raise RuntimeError(f"Connection error: {exc}") from exc


def api_call(
    firewall: Firewall,
    api_key: str,
    params: Dict[str, str],
    method: str = "post",
) -> ET.Element:
    """
    Execute a PAN-OS XML API call and return the parsed XML root.

    Args:
        firewall: Firewall target.
        api_key: API key.
        params: Query parameters (type/action/xpath/etc).
        method: HTTP method ("get" or "post").
    """

    request_params = dict(params)
    request_params["key"] = api_key

    url = f"https://{firewall.hostname}/api/"
    request_fn = requests.get if method.lower() == "get" else requests.post

    response = request_fn(
        url,
        params=request_params if method.lower() == "get" else None,
        data=None if method.lower() == "get" else request_params,
        verify=False,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()

    response_text = response.text
    root = ET.fromstring(response_text)
    if root.get("status") != "success":
        error_msg = root.findtext(".//msg") or root.findtext(".//line")
        raise RuntimeError(
            f"PAN-OS API error on {firewall.name}: {error_msg or 'Unknown error'} "
            f"(raw: {response_text})"
        )
    return root


def list_security_rule_names(firewall: Firewall, api_key: str) -> List[str]:
    """
    Return the list of security rule names in order.
    """
    root = fetch_security_rules(firewall, api_key)
    entries = root.findall(".//result/security/rules/entry")
    return [entry.get("name", "") for entry in entries if entry.get("name")]


