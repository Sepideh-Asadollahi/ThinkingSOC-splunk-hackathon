"""Splunk auth/login XML response parsing."""

from __future__ import annotations

import xml.etree.ElementTree as ET


def _parse_session_key(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    for elem in root.iter():
        if elem.tag.endswith("sessionKey") and elem.text:
            return elem.text.strip()
    raise ValueError("sessionKey not found in Splunk login response")
