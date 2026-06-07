"""VirusTotal (API v3) IOC enrichment for SOC analysis."""

from __future__ import annotations

import base64
import ipaddress
import logging
import re
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple
from urllib.parse import quote, urlparse

import httpx

from config import Settings
from services.threat_intel.virustotal_schema import build_vt_summary

logger = logging.getLogger(__name__)

# RFC 2606 + special-use names — VT /domains returns HTTP 400 for these.
_RESERVED_DOMAIN_SUFFIXES: Tuple[str, ...] = (
    ".example",
    ".test",
    ".invalid",
    ".localhost",
)

# Internal / AD-style suffixes — not suitable for VT /domains (skip before API call).
_INTERNAL_DOMAIN_SUFFIXES: Tuple[str, ...] = (
    ".local",
    ".lan",
    ".internal",
    ".intranet",
    ".corp",
    ".home",
    ".localdomain",
    ".private",
    ".ad",
)

# --- Regex helpers (secondary extraction from string values) -----------------
_RE_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")
_RE_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
_RE_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
_RE_URL = re.compile(r"\bhttps?://[^\s\"'<>]+", re.IGNORECASE)
_RE_IP_TOKEN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    r"|\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"
)

# --- Splunk CIM–style field names (lowercase) --------------------------------
# Network traffic, DNS, proxy, auth, endpoint, web — common aliases.
_CIM_IP_FIELDS: FrozenSet[str] = frozenset(
    {
        "src_ip",
        "dest_ip",
        "client_ip",
        "server_ip",
        "orig_src_ip",
        "orig_dest_ip",
        "srcipv4",
        "destipv4",
        "srcipv6",
        "destipv6",
        "ip",
        "host_ip",
        "dvc_ip",
        "device_ip",
        "answer",  # DNS A/AAAA often here
        "dns_answer",
        "relay_ip",
        "forwardedfor",
        "xff",
        "x_forwarded_for",
        "x_forwarded_for_ip",
        "true_client_ip",
        "src_nat",
        "dest_nat",
        "src_nat_ip",
        "dest_nat_ip",
        "vendor_ip",
        "remote_ip",
        "external_ip",
        "internal_ip",  # name is ambiguous; still filtered to public before VT
    }
)

# `src` / `dest` are CIM dimensions: often IP in Network Traffic; sometimes hostname.
_CIM_SRC_DEST_AS_IP: FrozenSet[str] = frozenset({"src", "dest"})

_CIM_HASH_FIELDS: FrozenSet[str] = frozenset(
    {
        "md5",
        "sha1",
        "sha256",
        "sha_256",
        "sha_1",
        "hash",
        "hashes",
        "file_hash",
        "file_md5",
        "file_sha1",
        "file_sha256",
        "process_hash",
        "process_md5",
        "process_sha256",
        "parent_process_hash",
        "parent_process_md5",
        "parent_process_sha256",
        "module_hash",
        "certificate_hash",
    }
)

_CIM_URL_FIELDS: FrozenSet[str] = frozenset(
    {
        "url",
        "http_uri",
        "cs_uri",
        "cs_uri_stem",
        "cs_uri_query",
        "uri",
        "uri_path",
        "page_url",
        "referer",
        "referrer",
        "http_referrer",
        "http_referer",
    }
)

_CIM_DOMAIN_FIELDS: FrozenSet[str] = frozenset(
    {
        "fqdn",
        "domain",
        "dns_query",
        "url_domain",
        "http_hostname",
        "cs_host",
        "mail_from_domain",
        "dest_host",
        "src_host",
        "dest_nt_host",
        "src_nt_host",
    }
)

# Union of Splunk CIM field names whose values may yield VT IOCs (primary + regex scan).
_VT_IOC_FIELDS: FrozenSet[str] = (
    _CIM_HASH_FIELDS | _CIM_IP_FIELDS | _CIM_URL_FIELDS | _CIM_DOMAIN_FIELDS | _CIM_SRC_DEST_AS_IP
)


def is_public_ip(addr: str) -> bool:
    """
    True only for globally routable addresses suitable for VT /ip_addresses/{ip}.

    Private (RFC1918), loopback, link-local, multicast, reserved, documentation, etc. are excluded.
    Uses ``IPv4Address.is_global`` / ``IPv6Address.is_global`` when available (Python 3.8+).
    """
    s = (addr or "").strip().strip('"').strip("'")
    if not s:
        return False
    try:
        ip = ipaddress.ip_address(s)
    except ValueError:
        return False
    if getattr(ip, "is_global", None) is not None:
        return bool(ip.is_global)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or getattr(ip, "is_reserved", False)
        or getattr(ip, "is_site_local", False)
    )


def _norm_key(k: Any) -> str:
    return str(k or "").strip().lower()


def _split_mv(val: str) -> List[str]:
    """Splunk multivalue-ish strings: newline, pipe, semicolon, comma."""
    if not val:
        return []
    parts = re.split(r"[\n\r\t|,;]+", val)
    return [p.strip().strip('"').strip("'") for p in parts if p.strip()]


def _yield_scalar_values(v: Any) -> Iterable[str]:
    if v is None:
        return
    if isinstance(v, str):
        yield v
        return
    if isinstance(v, (int, float, bool)):
        yield str(v)
        return
    if isinstance(v, list):
        for x in v:
            yield from _yield_scalar_values(x)


def _extract_hashes_from_text(text: str) -> List[str]:
    if not text:
        return []
    # dict preserves insertion order; avoids O(n²) "m not in list" dedup on large alerts.
    found: Dict[str, None] = {}
    for rx in (_RE_SHA256, _RE_SHA1, _RE_MD5):
        for m in rx.findall(text):
            found.setdefault(m, None)
    return list(found.keys())


def _host_from_url(url: str) -> Optional[str]:
    try:
        p = urlparse(url.strip())
    except Exception:
        return None
    host = (p.hostname or "").strip().lower()
    if not host or host.endswith(".onion"):
        return None
    return host


def domain_vt_skip_reason(domain: str) -> Optional[str]:
    """
    Return a human-readable reason when a hostname must not be sent to VT /domains.

    Demo Splunk data often uses ``*.example`` (RFC 2606) or short hostnames — VT answers 400.
    """
    d = (domain or "").strip().lower().strip('"').strip("'")
    if not d:
        return "empty domain"
    if "." not in d:
        return (
            "not an FQDN (no dot) — VirusTotal /domains/{{domain}} requires a fully qualified "
            "domain name, not a short hostname like '{0}'"
        ).format(d)
    for suf in _RESERVED_DOMAIN_SUFFIXES:
        if d == suf.lstrip(".") or d.endswith(suf):
            return (
                "reserved/documentation TLD '{0}' (RFC 2606) — not a routable internet domain; "
                "VirusTotal rejects *.example / *.test style demo names with HTTP 400"
            ).format(suf)
    for suf in _INTERNAL_DOMAIN_SUFFIXES:
        if d == suf.lstrip(".") or d.endswith(suf):
            return (
                "internal/private domain suffix '{0}' — not a public internet FQDN suitable for "
                "VirusTotal /domains lookup"
            ).format(suf)
    return None


def _maybe_domain(hostname: str) -> Optional[str]:
    """
    Keep hostname/FQDN for VT domain report; drop values that are clearly IPs.
    """
    h = (hostname or "").strip().lower().strip('"').strip("'")
    if not h or len(h) > 253:
        return None
    try:
        ipaddress.ip_address(h)
        return None
    except ValueError:
        pass
    if " " in h or "/" in h or "\\" in h:
        return None
    if not re.match(r"^[a-z0-9._-]+$", h, re.IGNORECASE):
        return None
    return h


def _parse_vt_error_body(response: httpx.Response) -> str:
    """Best-effort VT API v3 error message from response body."""
    try:
        body = response.json()
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, dict):
                code = err.get("code")
                msg = err.get("message")
                if code and msg:
                    return "{0}: {1}".format(code, msg)
                if msg:
                    return str(msg)
                if code:
                    return str(code)
            return str(body)[:400]
    except Exception:
        pass
    text = (response.text or "").strip()
    return text[:400] if text else "no response body"


def _http_failure_reason(
    status_code: int,
    ioc_kind: str,
    ioc_value: str,
    vt_detail: str,
) -> str:
    """Analyst-facing short reason (also stored on the IOC entry)."""
    skip = domain_vt_skip_reason(ioc_value) if ioc_kind == "domain" else None
    if skip:
        return skip
    if status_code == 400 and ioc_kind == "domain":
        return (
            "VirusTotal rejected domain (HTTP 400). Often an invalid/non-public FQDN, "
            "internal AD name, or placeholder TLD. VT: {0}"
        ).format(vt_detail or "Bad Request")
    if status_code == 401:
        return "VirusTotal API key invalid or missing (HTTP 401)"
    if status_code == 403:
        return "VirusTotal forbidden — quota or permission (HTTP 403): {0}".format(vt_detail)
    if status_code == 429:
        return "VirusTotal rate limit (HTTP 429)"
    return "VirusTotal HTTP {0}: {1}".format(status_code, vt_detail or "error")


def _iter_alert_field_pairs(
    normalized: Dict[str, Any],
    splunk_results_preview: List[Dict[str, Any]],
) -> Iterable[Tuple[str, str]]:
    """(lowercase_field_name, string_value) from normalized + preview rows."""
    def walk(d: Dict[str, Any]) -> Iterable[Tuple[str, str]]:
        for k, v in d.items():
            nk = _norm_key(k)
            if nk.startswith("__mv_"):
                continue
            for sv in _yield_scalar_values(v):
                if sv:
                    yield nk, sv

    if isinstance(normalized, dict):
        yield from walk(normalized)
    for row in splunk_results_preview[:5]:
        if isinstance(row, dict):
            yield from walk(row)


def extract_iocs(
    normalized: Dict[str, Any],
    splunk_results_preview: List[Dict[str, Any]],
    *,
    max_iocs: int,
) -> Dict[str, List[str]]:
    """
    Extract IOCs for VirusTotal: file hashes, **public** IPs only, domains, URLs.

    Primary source: **CIM-compatible field names** on the alert / Splunk preview rows.
    Secondary: hash, URL, and public-IP regex only on those same VT-scoped field values.
    Generic host/computer fields (e.g. ``host``, ``Computer``) are ignored for domain IOCs.
    Internal/private FQDNs (``.local``, ``.corp``, short hostnames, RFC 2606) are skipped.
    """
    max_iocs = max(0, int(max_iocs))
    empty = {"file_hashes": [], "ips": [], "domains": [], "urls": []}
    if max_iocs == 0:
        return empty

    file_hashes: List[str] = []
    ips: List[str] = []
    domains: List[str] = []
    urls: List[str] = []

    def cap() -> int:
        return len(file_hashes) + len(ips) + len(domains) + len(urls)

    def add_hashes(items: Iterable[str]) -> None:
        for h in items:
            if cap() >= max_iocs:
                return
            hx = h.lower()
            if len(hx) not in (32, 40, 64):
                continue
            if not re.fullmatch(r"[a-f0-9]+", hx):
                continue
            if hx not in file_hashes:
                file_hashes.append(hx)

    def add_ips(items: Iterable[str]) -> None:
        for raw in items:
            if cap() >= max_iocs:
                return
            for token in _split_mv(raw):
                if is_public_ip(token) and token not in ips:
                    ips.append(token)

    def add_domains(items: Iterable[str]) -> None:
        for raw in items:
            if cap() >= max_iocs:
                return
            for token in _split_mv(raw):
                dom = _maybe_domain(token)
                if not dom or dom in domains:
                    continue
                if domain_vt_skip_reason(dom):
                    continue
                domains.append(dom)

    def add_urls(items: Iterable[str]) -> None:
        for raw in items:
            if cap() >= max_iocs:
                return
            u = (raw or "").strip().strip('"').strip("'")
            if u.lower().startswith(("http://", "https://")) and u not in urls:
                urls.append(u)

    pairs = list(_iter_alert_field_pairs(normalized, splunk_results_preview))

    # 1) CIM-keyed extraction
    for nk, sv in pairs:
        if cap() >= max_iocs:
            break
        if nk in _CIM_HASH_FIELDS:
            add_hashes(_extract_hashes_from_text(sv))
            # whole field may be exactly one hash
            t = sv.strip().lower()
            if re.fullmatch(r"[a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64}", t):
                add_hashes([t])
        elif nk in _CIM_IP_FIELDS:
            add_ips([sv])
        elif nk in _CIM_SRC_DEST_AS_IP:
            for token in _split_mv(sv):
                if is_public_ip(token):
                    add_ips([token])
        elif nk in _CIM_URL_FIELDS:
            add_urls([sv])
            for u in _RE_URL.findall(sv):
                add_urls([u])
        elif nk in _CIM_DOMAIN_FIELDS:
            for token in _split_mv(sv):
                if is_public_ip(token):
                    add_ips([token])
                else:
                    add_domains([token])

    # 2) Regex on VT-scoped field values only: URLs, hashes, public IPs (no domain-regex on free text)
    if cap() < max_iocs:
        for nk, sv in pairs:
            if cap() >= max_iocs:
                break
            if nk not in _VT_IOC_FIELDS:
                continue
            if len(sv) > 8000:
                continue
            add_urls(_RE_URL.findall(sv))
            add_hashes(_extract_hashes_from_text(sv))
            for ipm in _RE_IP_TOKEN.findall(sv):
                if is_public_ip(ipm):
                    add_ips([ipm])

    # Domains from URLs collected so far
    if cap() < max_iocs:
        for u in list(urls):
            hf = _host_from_url(u)
            if hf:
                add_domains([hf])

    # Trim to max_iocs total across categories (priority: hash, ip, url, domain)
    out = {"file_hashes": [], "ips": [], "domains": [], "urls": []}
    for h in file_hashes:
        if len(out["file_hashes"]) + len(out["ips"]) + len(out["domains"]) + len(out["urls"]) >= max_iocs:
            break
        out["file_hashes"].append(h)
    for ip in ips:
        if len(out["file_hashes"]) + len(out["ips"]) + len(out["domains"]) + len(out["urls"]) >= max_iocs:
            break
        out["ips"].append(ip)
    for u in urls:
        if len(out["file_hashes"]) + len(out["ips"]) + len(out["domains"]) + len(out["urls"]) >= max_iocs:
            break
        out["urls"].append(u)
    for d in domains:
        if len(out["file_hashes"]) + len(out["ips"]) + len(out["domains"]) + len(out["urls"]) >= max_iocs:
            break
        out["domains"].append(d)

    return out


def _url_id_base64(url: str) -> str:
    # VT docs: unpadded base64url (RFC 4648) of the URL; canonicalization is server-side.
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").rstrip("=")


class VirusTotalClient:
    def __init__(self, settings: Settings):
        self._base = settings.virustotal_base_url.rstrip("/")
        self._key = (settings.virustotal_api_key or "").strip()
        self._timeout = float(settings.virustotal_timeout_seconds)

    def configured(self) -> bool:
        return bool(self._key)

    def _headers(self) -> Dict[str, str]:
        return {"accept": "application/json", "x-apikey": self._key}

    async def _get_json(
        self,
        path: str,
        *,
        ioc_kind: str,
        ioc_value: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        url = self._base + path
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(url, headers=self._headers())
                if r.status_code == 404:
                    logger.info(
                        "virustotal %s not in VT database %s=%s",
                        ioc_kind,
                        ioc_kind,
                        ioc_value,
                    )
                    return None, "not_found"
                if r.status_code >= 400:
                    vt_detail = _parse_vt_error_body(r)
                    reason = _http_failure_reason(r.status_code, ioc_kind, ioc_value, vt_detail)
                    logger.warning(
                        "virustotal %s lookup failed %s=%s http=%s reason=%s vt_detail=%s url=%s",
                        ioc_kind,
                        ioc_kind,
                        ioc_value,
                        r.status_code,
                        reason,
                        vt_detail,
                        url,
                    )
                    return None, "http_{0}: {1}".format(r.status_code, reason)
                return r.json(), None
        except httpx.TimeoutException as e:
            logger.warning(
                "virustotal %s lookup timeout %s=%s timeout_s=%s err=%s",
                ioc_kind,
                ioc_kind,
                ioc_value,
                self._timeout,
                e,
            )
            return None, "timeout: {0}".format(e)
        except httpx.RequestError as e:
            logger.warning(
                "virustotal %s lookup transport error %s=%s err=%s",
                ioc_kind,
                ioc_kind,
                ioc_value,
                e,
            )
            return None, "transport: {0}".format(e)
        except Exception as e:
            logger.warning(
                "virustotal %s lookup error %s=%s err=%s",
                ioc_kind,
                ioc_kind,
                ioc_value,
                e,
            )
            return None, "error: {0}".format(e)

    async def file_report(self, file_hash: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return await self._get_json(
            "/files/{0}".format(quote(file_hash, safe="")),
            ioc_kind="file_hash",
            ioc_value=file_hash,
        )

    async def domain_report(self, domain: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        skip = domain_vt_skip_reason(domain)
        if skip:
            logger.info(
                "virustotal domain lookup skipped domain=%s reason=%s",
                domain,
                skip,
            )
            return None, "skipped: {0}".format(skip)
        return await self._get_json(
            "/domains/{0}".format(quote(domain, safe="")),
            ioc_kind="domain",
            ioc_value=domain,
        )

    async def ip_report(self, ip: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return await self._get_json(
            "/ip_addresses/{0}".format(quote(ip, safe="")),
            ioc_kind="ip",
            ioc_value=ip,
        )

    async def url_report(self, url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        url_id = _url_id_base64(url)
        return await self._get_json(
            "/urls/{0}".format(quote(url_id, safe="")),
            ioc_kind="url",
            ioc_value=url,
        )


async def enrich_virustotal(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    splunk_results_preview: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Query VT for supported IOCs and return a compact enrichment object to inject into System Context.
    """
    if not settings.virustotal_enable:
        logger.debug("virustotal skipped (disabled)")
        return {"enabled": False}

    client = VirusTotalClient(settings)
    if not client.configured():
        logger.info("virustotal skipped (no_api_key)")
        return {"enabled": False, "reason": "no_api_key"}

    iocs = extract_iocs(
        normalized,
        splunk_results_preview,
        max_iocs=settings.virustotal_max_iocs,
    )
    logger.info(
        "virustotal enrich iocs file_hashes=%d ips=%d domains=%d urls=%d",
        len(iocs["file_hashes"]),
        len(iocs["ips"]),
        len(iocs["domains"]),
        len(iocs["urls"]),
    )

    results: Dict[str, Any] = {
        "enabled": True,
        "requested": iocs,
        "files": {},
        "ips": {},
        "domains": {},
        "urls": {},
    }

    for h in iocs["file_hashes"]:
        data, err = await client.file_report(h)
        results["files"][h] = {"error": err, "summary": build_vt_summary(data)}
        if err and err != "not_found":
            logger.info("virustotal file_hash=%s enrichment_error=%s", h, err)
    for ip in iocs["ips"]:
        data, err = await client.ip_report(ip)
        results["ips"][ip] = {"error": err, "summary": build_vt_summary(data)}
        if err and err != "not_found":
            logger.info("virustotal ip=%s enrichment_error=%s", ip, err)
    for d in iocs["domains"]:
        data, err = await client.domain_report(d)
        results["domains"][d] = {"error": err, "summary": build_vt_summary(data)}
        if err and err != "not_found":
            logger.info("virustotal domain=%s enrichment_error=%s", d, err)
    for u in iocs["urls"]:
        data, err = await client.url_report(u)
        results["urls"][u] = {"error": err, "summary": build_vt_summary(data)}
        if err and err != "not_found":
            logger.info("virustotal url=%s enrichment_error=%s", u, err)

    return results
