#!/usr/bin/env python3
"""
List the current security policies on Baker Street Labs cyber range firewalls.

The script:
  * Loads credentials from the user's ~/.secrets file (key=value format).
  * Tests PAN-OS XML API connectivity for Range Agentix, Range XDR, and Range XSIAM.
  * When authentication succeeds, retrieves and prints the security rulebase.

Credential lookup order for each firewall:
  1. <FIREWALL_NAME>_API_KEY  (e.g. RANGEXDR_API_KEY)
  2. PANOS_API_KEY            (shared key for all firewalls)
  3. PANOS_USERNAME + PANOS_PASSWORD (used to request a fresh API key)

Outputs a structured text summary by default and can emit JSON for automation.
"""

from __future__ import annotations

import argparse
import json
import ssl
from typing import Dict, Iterable, List
import xml.etree.ElementTree as ET

import requests
import urllib3

from panos_api import (
    SecretsError,
    iter_firewalls,
    load_secrets,
    resolve_api_key,
    fetch_security_rules,
    Firewall,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _members(entry: ET.Element, tag: str) -> List[str]:
    node = entry.find(tag)
    if node is None:
        return ["any"]
    members = [member.text for member in node.findall("member") if member.text]
    return members or ["any"]


def parse_rules(xml_root: ET.Element) -> List[Dict[str, object]]:
    """Convert the XML rulebase into structured dictionaries."""
    rule_entries = xml_root.findall(".//result/security/rules/entry")
    rules: List[Dict[str, object]] = []

    for entry in rule_entries:
        rule = {
            "name": entry.get("name", ""),
            "description": entry.findtext("description") or "",
            "from": _members(entry, "from"),
            "to": _members(entry, "to"),
            "source": _members(entry, "source"),
            "destination": _members(entry, "destination"),
            "application": _members(entry, "application"),
            "service": _members(entry, "service"),
            "category": _members(entry, "category"),
            "action": entry.findtext("action") or "allow",
            "log_setting": entry.findtext("log-setting") or "",
            "disabled": (entry.findtext("disabled") or "no").lower() == "yes",
        }
        rules.append(rule)

    return rules


def print_rules_text(firewall: Firewall, rules: Iterable[Dict[str, object]]) -> None:
    print("=" * 80)
    print(f"{firewall.description} ({firewall.hostname})")
    print("=" * 80)

    rule_list = list(rules)
    if not rule_list:
        print("No security policies found.")
        print()
        return

    for rule in rule_list:
        status = "disabled" if rule["disabled"] else "enabled"
        print(f"Rule: {rule['name']} ({status})")
        if rule["description"]:
            print(f"  Description : {rule['description']}")
        print(f"  From        : {', '.join(rule['from'])}")
        print(f"  To          : {', '.join(rule['to'])}")
        print(f"  Source      : {', '.join(rule['source'])}")
        print(f"  Destination : {', '.join(rule['destination'])}")
        print(f"  Application : {', '.join(rule['application'])}")
        print(f"  Service     : {', '.join(rule['service'])}")
        print(f"  Category    : {', '.join(rule['category'])}")
        print(f"  Action      : {rule['action']}")
        if rule["log_setting"]:
            print(f"  Log Setting : {rule['log_setting']}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test PAN-OS API connectivity and list security policies.",
    )
    parser.add_argument(
        "--firewall",
        choices=sorted(fw.name for fw in iter_firewalls()),
        help="Limit to a single firewall instead of querying all.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for security policies (default: text).",
    )

    args = parser.parse_args()

    try:
        secrets = load_secrets()
    except SecretsError as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc

    selected_firewalls = list(iter_firewalls(args.firewall))

    results: Dict[str, List[Dict[str, object]]] = {}

    for firewall in selected_firewalls:
        print(f"[*] Testing API access to {firewall.name} ({firewall.hostname})...")
        try:
            api_key = resolve_api_key(firewall, secrets)
        except SecretsError as exc:
            print(f"[WARN] {exc}")
            continue

        try:
            xml_root = fetch_security_rules(firewall, api_key)
            rules = parse_rules(xml_root)
            results[firewall.name] = rules
            print(f"[OK] Retrieved {len(rules)} security policy rules.")
        except (requests.RequestException, ssl.SSLError) as exc:
            print(f"[ERROR] Connection to {firewall.hostname} failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] Unable to process rules for {firewall.name}: {exc}")

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return

    for firewall in selected_firewalls:
        rules = results.get(firewall.name)
        if rules is None:
            print("=" * 80)
            print(f"{firewall.description} ({firewall.hostname})")
            print("=" * 80)
            print("No data retrieved.")
            print()
            continue
        print_rules_text(firewall, rules)


if __name__ == "__main__":
    main()


