#!/usr/bin/env python3
"""
Deploy recommended security rules to the Range XSIAM firewall.

The rules are inserted immediately *after* the existing "Lab Learning Policy"
rule so they remain shadowed until reviewed.

Requirements:
  * API key for Range XSIAM present in ~/.secrets (RANGEXSIAM_API_KEY or fallback)
  * CSV file generated at data/panos-recommended-rules.csv
"""

from __future__ import annotations

import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List

from panos_api import (
    FIREWALLS,
    RULEBASE_XPATH,
    api_call,
    list_security_rule_names,
    load_secrets,
    resolve_api_key,
)

CSV_PATH = Path("range-prep-tool/panos-recommended-rules.csv")
TARGET_FIREWALL = FIREWALLS["rangexsiam"]
LOG_PROFILE_NAME = "default"
ANCHOR_RULE = "Lab Learning Policy"

PROFILE_TAGS = {
    "anti-virus": "virus",
    "anti-spyware": "spyware",
    "vulnerability-protection": "vulnerability",
    "url-filtering": "url-filtering",
}


def split_members(field: str) -> List[str]:
    field = field.strip()
    if not field:
        return ["any"]
    if field.lower() == "any":
        return ["any"]
    return [item.strip() for item in field.split("|") if item.strip()]


def build_member_nodes(
    parent: ET.Element,
    tag: str,
    values: Iterable[str],
    *,
    skip_any: bool = False,
) -> None:
    values = list(values)
    if skip_any and len(values) == 1 and values[0].lower() == "any":
        return

    node = ET.SubElement(parent, tag)
    for value in values:
        ET.SubElement(node, "member").text = value


def build_security_rule_entry(rule: Dict[str, str]) -> ET.Element:
    entry = ET.Element("entry", {"name": rule["rule_name"]})

    build_member_nodes(entry, "from", split_members(rule["source_zone"]))
    build_member_nodes(entry, "to", split_members(rule["destination_zone"]))
    build_member_nodes(entry, "source", split_members(rule["source_address"]))
    build_member_nodes(entry, "destination", split_members(rule["destination_address"]))
    build_member_nodes(
        entry,
        "application",
        split_members(rule["application"]),
        skip_any=True,
    )
    build_member_nodes(
        entry,
        "service",
        split_members(rule["service"]),
        skip_any=True,
    )

    # Default additional fields
    build_member_nodes(entry, "source-user", ["any"])

    ET.SubElement(entry, "action").text = rule["action"]
    ET.SubElement(entry, "log-start").text = "no"
    ET.SubElement(entry, "log-end").text = "yes"
    ET.SubElement(entry, "log-setting").text = LOG_PROFILE_NAME
    ET.SubElement(entry, "disabled").text = "no"

    description = rule.get("description") or ""
    if description:
        ET.SubElement(entry, "description").text = description

    security_profiles = split_members(rule.get("security_profiles", ""))
    profile_entries = [
        PROFILE_TAGS.get(profile.lower())
        for profile in security_profiles
        if profile and profile.lower() != "none"
    ]
    if profile_entries:
        profile_setting = ET.SubElement(entry, "profile-setting")
        profiles = ET.SubElement(profile_setting, "profiles")
        for profile in security_profiles:
            tag = PROFILE_TAGS.get(profile.lower())
            if not tag:
                continue
            node = ET.SubElement(profiles, tag)
            ET.SubElement(node, "member").text = LOG_PROFILE_NAME

    return entry


def load_rules_from_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"[ERROR] CSV file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def main() -> None:
    secrets = load_secrets()
    api_key = resolve_api_key(TARGET_FIREWALL, secrets)

    rules = load_rules_from_csv(CSV_PATH)
    existing_rules = set(list_security_rule_names(TARGET_FIREWALL, api_key))

    created = []
    skipped = []

    for rule in rules:
        rule_name = rule["rule_name"]
        if rule_name in existing_rules:
            skipped.append(rule_name)
            continue

        entry = build_security_rule_entry(rule)
        element_xml = ET.tostring(entry, encoding="unicode")

        api_call(
            TARGET_FIREWALL,
            api_key,
            params={
                "type": "config",
                "action": "set",
                "xpath": f"{RULEBASE_XPATH}/rules",
                "element": element_xml,
            },
        )

        api_call(
            TARGET_FIREWALL,
            api_key,
            params={
                "type": "config",
                "action": "move",
                "xpath": f"{RULEBASE_XPATH}/rules/entry[@name='{rule_name}']",
                "where": "after",
                "dst": ANCHOR_RULE,
            },
        )

        created.append(rule_name)

    if created:
        print(f"[OK] Created {len(created)} rule(s): {', '.join(created)}")
    else:
        print("[INFO] No new rules created.")

    if skipped:
        print(f"[INFO] Skipped existing rule(s): {', '.join(skipped)}")

    print("Changes staged on Range XSIAM. Commit manually after review.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}")
        sys.exit(1)


