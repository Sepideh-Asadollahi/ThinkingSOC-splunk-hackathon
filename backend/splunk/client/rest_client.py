"""
Splunk REST client (management port, default 8089). Splunk Enterprise / Splunk Cloud 10.x+ only:

- POST /services/auth/login — sessionKey (XML). RESTREF RESTaccess.
- GET /services/search/jobs/{search_id} — job status/metadata; output_mode=json.
- GET /services/search/v2/jobs/{search_id}/results — transformed results (params: output_mode=json,
  count, offset). RESTREF RESTsearch.
- POST /servicesNS/{owner}/{app}/search/jobs — oneshot search (exec_mode=oneshot).
- POST /servicesNS/{owner}/{app}/search/v2/parser — SPL parser (parse_only=true), Splunk 10+.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

import httpx

from config import Settings

from .http_utils import mgmt_netloc, truncate_log
from .oneshot_json import parse_oneshot_json
from .session import _parse_session_key

logger = logging.getLogger(__name__)


def _httpx_error_detail(exc: httpx.HTTPStatusError) -> str:
    """Extract Splunk/SAIA error text from an HTTP error response."""
    resp = exc.response
    if resp is None:
        return str(exc)
    text = (resp.text or "").strip()
    try:
        data = resp.json()
    except Exception:
        return text[:2000] or str(exc)
    if not isinstance(data, dict):
        return text[:2000] or str(exc)
    if data.get("error"):
        return str(data["error"])[:2000]
    entries = data.get("entry")
    if isinstance(entries, list) and entries:
        content = entries[0].get("content") if isinstance(entries[0], dict) else None
        if isinstance(content, dict):
            payload = content.get("payload")
            if isinstance(payload, str):
                try:
                    inner = json.loads(payload)
                    if isinstance(inner, dict) and inner.get("error"):
                        return str(inner["error"])[:2000]
                except json.JSONDecodeError:
                    return payload[:2000]
            if content.get("error"):
                return str(content["error"])[:2000]
    return text[:2000] or str(exc)


class SplunkRestClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.splunk_mgmt_url.rstrip("/") + "/"
        self._user = settings.splunk_username
        self._password = settings.splunk_password
        self._verify = settings.splunk_verify_ssl

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(verify=self._verify, timeout=120.0)

    async def login(self) -> str:
        if not self._user or not self._password:
            raise ValueError("splunk_username and splunk_password must be set for REST login")
        url = urljoin(self._base, "services/auth/login")
        data = {"username": self._user, "password": self._password}
        async with self._client() as client:
            try:
                r = await client.post(url, data=data)
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "splunk_rest login HTTP %s user=%s host=%s",
                    e.response.status_code,
                    self._user,
                    mgmt_netloc(self._base),
                )
                raise
            except httpx.RequestError as e:
                logger.warning(
                    "splunk_rest login transport error user=%s host=%s: %s",
                    self._user,
                    mgmt_netloc(self._base),
                    e,
                )
                raise
            body = r.text
        logger.info(
            "splunk_rest login ok user=%s host=%s",
            self._user,
            mgmt_netloc(self._base),
        )
        return _parse_session_key(body)

    def _auth_headers(self, session_key: str) -> Dict[str, str]:
        return {"Authorization": "Splunk {0}".format(session_key)}

    async def predict_spl_via_ui_path(
        self,
        session_key: str,
        *,
        prompt: str,
        source_app_id: str = "ThinkingSOC_Hackathon",
        app: str = "Splunk_AI_Assistant_Cloud",
        owner: str = "nobody",
        timeout_seconds: float = 25.0,
        poll_interval_seconds: float = 0.75,
    ) -> str:
        """
        Generate SPL via Splunk AI Assistant chat path (``/predict``), then poll chat history.
        """
        chat_id = str(uuid.uuid4())
        payload = {
            "prompt": prompt,
            "classification": 0,  # write_spl mode (same as UI Suggest SPL)
            "chat_id": chat_id,
        }
        enc_owner = quote(owner, safe="")
        enc_app = quote(app, safe="")
        predict_url = urljoin(
            self._base,
            "servicesNS/{0}/{1}/predict?output_mode=json".format(enc_owner, enc_app),
        )
        headers = self._auth_headers(session_key)
        headers["Content-Type"] = "application/json"
        headers["Source-App-ID"] = source_app_id

        async with self._client() as client:
            body: Dict[str, Any] = {}
            last_err = ""
            for attempt in range(1, 3):
                try:
                    logger.info(
                        "predict POST attempt=%d url=%s source_app=%s prompt_len=%d",
                        attempt,
                        predict_url,
                        source_app_id,
                        len(prompt or ""),
                    )
                    r = await client.post(predict_url, headers=headers, json=payload)
                    if r.status_code >= 400:
                        last_err = (r.text or "")[:2000]
                        will_retry = (
                            r.status_code in (500, 502, 503, 429) and attempt < 2
                        )
                        logger.debug(
                            "predict POST HTTP %s attempt=%d%s body=%s",
                            r.status_code,
                            attempt,
                            " (will retry)" if will_retry else " (final)",
                            truncate_log(last_err, 500),
                        )
                        if will_retry:
                            await asyncio.sleep(2.0)
                            continue
                        r.raise_for_status()
                    body = r.json()
                    break
                except httpx.HTTPStatusError as e:
                    last_err = _httpx_error_detail(e)
                    status = e.response.status_code if e.response else "?"
                    will_retry = (
                        e.response is not None
                        and e.response.status_code in (500, 502, 503, 429)
                        and attempt < 2
                    )
                    logger.debug(
                        "predict POST HTTP %s attempt=%d%s: %s",
                        status,
                        attempt,
                        " (will retry)" if will_retry else " (final)",
                        truncate_log(last_err, 500),
                    )
                    if will_retry:
                        await asyncio.sleep(2.0)
                        continue
                    raise RuntimeError(
                        "predict request failed (HTTP {0}): {1}".format(
                            status,
                            last_err,
                        )
                    ) from e
                except Exception as e:
                    raise RuntimeError("predict request failed: {0}".format(e)) from e
            else:
                raise RuntimeError(
                    "predict request failed after retries: {0}".format(last_err or "unknown")
                )
            response_id = str(body.get("response_id") or body.get("job_id") or "").strip()
            if not response_id:
                raise RuntimeError("predict response missing response_id")
            logger.info(
                "predict accepted chat_id=%s response_id=%s (polling chathistory up to %.0fs)",
                chat_id[:8],
                response_id[:8],
                timeout_seconds,
            )

            history_url = urljoin(
                self._base,
                "servicesNS/{0}/{1}/chathistory/{2}?output_mode=json".format(
                    enc_owner, enc_app, quote(chat_id, safe="")
                ),
            )
            deadline = time.monotonic() + max(5.0, float(timeout_seconds))
            poll_n = 0
            last_state = -1
            last_len = 0
            while time.monotonic() < deadline:
                poll_n += 1
                hr = await client.get(
                    history_url,
                    headers={"Authorization": headers["Authorization"], "Source-App-ID": source_app_id},
                    params={"include_records": "true"},
                )
                hr.raise_for_status()
                entry = _find_chat_entry_by_id(hr.json(), response_id)
                if entry is None:
                    logger.info(
                        "predict poll #%d chat_id=%s response_id=%s entry=missing elapsed=%.1fs",
                        poll_n,
                        chat_id[:8],
                        response_id[:8],
                        deadline - time.monotonic(),
                    )
                    await asyncio.sleep(max(0.2, float(poll_interval_seconds)))
                    continue
                state = int(entry.get("loadingState") or 0)
                content = str(entry.get("content") or "")
                if state != last_state or len(content) != last_len:
                    logger.info(
                        "predict poll #%d loadingState=%d content_len=%d toolId=%s",
                        poll_n,
                        state,
                        len(content),
                        entry.get("toolId") or "",
                    )
                    last_state, last_len = state, len(content)
                if state == 3:
                    raise RuntimeError(content or "predict returned error state")
                if state in (2, 4) and content.strip():
                    logger.info("predict done polls=%d final_state=%d", poll_n, state)
                    return content.strip()
                await asyncio.sleep(max(0.2, float(poll_interval_seconds)))

        raise TimeoutError(
            "predict response polling timed out after {0:.0f}s (polls={1}, last_loadingState={2}, last_content_len={3})".format(
                timeout_seconds, poll_n, last_state, last_len
            )
        )

    async def get_job(self, sid: str, session_key: str) -> Dict[str, Any]:
        enc = quote(sid, safe="")
        path = "services/search/jobs/{0}".format(enc)
        url = urljoin(self._base, path)
        async with self._client() as client:
            try:
                r = await client.get(
                    url,
                    headers=self._auth_headers(session_key),
                    params={"output_mode": "json"},
                )
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "splunk_rest get_job HTTP %s sid=%s",
                    e.response.status_code,
                    sid,
                )
                raise
            except httpx.RequestError as e:
                logger.warning("splunk_rest get_job transport error sid=%s: %s", sid, e)
                raise
        logger.debug("splunk_rest get_job ok sid=%s", sid)
        return r.json()

    async def fetch_all_results(self, sid: str, session_key: str) -> List[Dict[str, Any]]:
        enc = quote(sid, safe="")
        rel = "services/search/v2/jobs/{0}/results".format(enc)
        out: List[Dict[str, Any]] = []
        offset = 0
        page_size = 50000
        headers = self._auth_headers(session_key)
        async with self._client() as client:
            while True:
                url = urljoin(self._base, rel)
                try:
                    r = await client.get(
                        url,
                        headers=headers,
                        params={
                            "output_mode": "json",
                            "count": page_size,
                            "offset": offset,
                        },
                    )
                    r.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        "splunk_rest fetch_results HTTP %s sid=%s offset=%s",
                        e.response.status_code,
                        sid,
                        offset,
                    )
                    raise
                except httpx.RequestError as e:
                    logger.warning(
                        "splunk_rest fetch_results transport sid=%s offset=%s: %s",
                        sid,
                        offset,
                        e,
                    )
                    raise
                data = r.json()
                batch = data.get("results") or []
                if not batch:
                    break
                out.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
        logger.info("splunk_rest fetch_results ok sid=%s total_rows=%d", sid, len(out))
        return out

    async def oneshot_search(
        self,
        session_key: str,
        spl: str,
        *,
        owner: str = "nobody",
        app: str,
        earliest_time: Optional[str] = None,
        latest_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run a blocking oneshot search in an app namespace (servicesNS).

        See Splunk REST: POST ``/servicesNS/{owner}/{app}/search/jobs`` with exec_mode=oneshot.

        ``count=0`` requests **all** result rows (Splunk default is 100). See RESTREF ``search/jobs``.
        """
        enc_owner = quote(owner, safe="")
        enc_app = quote(app, safe="")
        path = "servicesNS/{0}/{1}/search/jobs".format(enc_owner, enc_app)
        url = urljoin(self._base, path)
        form: Dict[str, Any] = {
            "search": spl,
            "exec_mode": "oneshot",
            "output_mode": "json",
            "count": 0,
        }
        if earliest_time:
            form["earliest_time"] = earliest_time
        if latest_time:
            form["latest_time"] = latest_time
        async with self._client() as client:
            try:
                r = await client.post(
                    url,
                    headers=self._auth_headers(session_key),
                    data=form,
                )
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "splunk_rest oneshot HTTP %s app=%s owner=%s spl_len=%d spl=%s",
                    e.response.status_code,
                    app,
                    owner,
                    len(spl or ""),
                    (spl or "")[:500],
                )
                raise
            except httpx.RequestError as e:
                logger.warning(
                    "splunk_rest oneshot transport app=%s owner=%s: %s",
                    app,
                    owner,
                    e,
                )
                raise
            try:
                payload = r.json()
            except Exception as e:
                logger.warning("splunk_rest oneshot response not JSON app=%s owner=%s", app, owner)
                raise RuntimeError("Splunk oneshot response is not JSON: {0}".format(e)) from e
        try:
            rows = parse_oneshot_json(payload)
        except RuntimeError as e:
            logger.warning(
                "splunk_rest oneshot spl error app=%s owner=%s spl_len=%d: %s",
                app,
                owner,
                len(spl or ""),
                e,
            )
            raise
        logger.info(
            "splunk_rest oneshot ok app=%s owner=%s rows=%d spl_len=%d",
            app,
            owner,
            len(rows),
            len(spl or ""),
        )
        return rows

    @staticmethod
    def _spl_query_for_parser(spl: str) -> str:
        """v2/parser: pass ``| tstats`` pipeline as-is (generating search is implicit)."""
        from services.investigation.spl_tstats_sanitize import normalize_tstats_spl

        s = normalize_tstats_spl(spl)
        if not s:
            return s
        low = s.lower()
        if low.startswith("search ") and "| tstats" in low:
            idx = re.search(r"\|\s*tstats\b", s, flags=re.IGNORECASE)
            if idx:
                return s[idx.start() :].strip()
        return s

    async def parse_spl(
        self,
        session_key: str,
        spl: str,
        *,
        owner: str = "nobody",
        app: str = "search",
    ) -> Dict[str, Any]:
        """
        Validate SPL via ``POST /servicesNS/{owner}/{app}/search/v2/parser``.

        Splunk 10+ removed GET on ``search/parser`` ("The method is not allowed").
        This endpoint **does not execute** the search — parse_only returns the AST.
        Raises ``ValueError`` on syntax errors (HTTP 400 with FATAL/ERROR messages).
        """
        # v2/parser lives under the ``search`` app — not Splunk_SA_CIM.
        if (app or "").strip().lower() not in ("search",):
            logger.debug("parse_spl forcing app=search (requested %s)", app)
            app = "search"
        enc_owner = quote(owner, safe="")
        enc_app = quote(app, safe="")
        path = "servicesNS/{0}/{1}/search/v2/parser".format(enc_owner, enc_app)
        url = urljoin(self._base, path)
        form: Dict[str, Any] = {
            "q": self._spl_query_for_parser(spl),
            "parse_only": "true",
            "output_mode": "json",
        }
        async with self._client() as client:
            try:
                r = await client.post(
                    url,
                    headers=self._auth_headers(session_key),
                    data=form,
                )
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "splunk_rest parse_spl HTTP %s app=%s owner=%s spl_len=%d",
                    e.response.status_code,
                    app,
                    owner,
                    len(spl or ""),
                )
                raise
            except httpx.RequestError as e:
                logger.warning(
                    "splunk_rest parse_spl transport app=%s owner=%s: %s",
                    app,
                    owner,
                    e,
                )
                raise
        if r.status_code >= 400:
            errs: List[str] = []
            try:
                data = r.json()
                for msg in (data.get("messages") or []):
                    if not isinstance(msg, dict):
                        continue
                    if str(msg.get("type", "")).upper() in ("ERROR", "FATAL"):
                        text = str(msg.get("text") or msg.get("message") or "")
                        if text:
                            errs.append(text)
            except Exception:
                pass
            if errs:
                logger.warning(
                    "splunk_rest parse_spl syntax app=%s owner=%s: %s",
                    app,
                    owner,
                    truncate_log("; ".join(errs), 800),
                )
                raise ValueError("; ".join(errs))
            logger.warning(
                "splunk_rest parse_spl HTTP %s app=%s owner=%s (no parser messages)",
                r.status_code,
                app,
                owner,
            )
            r.raise_for_status()
        out = r.json()
        logger.debug(
            "splunk_rest parse_spl ok app=%s owner=%s spl_len=%d",
            app,
            owner,
            len(spl or ""),
        )
        return out


def _find_chat_entry_by_id(payload: Dict[str, Any], response_id: str) -> Optional[Dict[str, Any]]:
    chat_history = payload.get("chat_history")
    if not isinstance(chat_history, dict):
        return None
    records = chat_history.get("records")
    if not isinstance(records, dict):
        return None
    for thread_entries in records.values():
        if not isinstance(thread_entries, list):
            continue
        for entry in thread_entries:
            if isinstance(entry, dict) and str(entry.get("id") or "") == response_id:
                return entry
    return None
