"""Typed async SDK client for ThinkingSOC backend APIs."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional, Type, TypeVar, Union

import httpx
from pydantic import BaseModel

from models.agentic_ops import AlertClassificationRequest, AlertClassificationResult, AnalysisRouteRequest, AnalysisRouteResponse
from models.agents import AgentTriageRequest, AgentTriageResponse
from models.analysis import AnalysisBatchBySidRequest, AnalysisBatchBySidResponse, AnalysisRunRequest, SocAnalysisResult
from models.assistant import SplAssistantSuggestRequest, SplAssistantSuggestResponse
from models.dashboard import DashboardOverview
from models.mcp import McpSplGenerateRequest, McpSplGenerateResponse, McpToolCallRequest, McpToolCallResponse
from models.observability import (
    ObservabilityAnalysisResult,
    ObservabilityBatchBySidRequest,
    ObservabilityBatchBySidResponse,
    ObservabilityRunRequest,
)
from services.soc_rag.models import SocChatRequest, SocChatResponse

from .errors import TsocApiError, TsocAuthError, TsocNotFoundError, TsocTimeoutError

ReqModel = Union[
    AlertClassificationRequest,
    AnalysisRouteRequest,
    AgentTriageRequest,
    SplAssistantSuggestRequest,
]
ResModel = TypeVar("ResModel", bound=BaseModel)


class AsyncTsocSdkClient:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:9876",
        ingest_token: Optional[str] = None,
        timeout_seconds: float = 120.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.4,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.ingest_token = ingest_token or os.environ.get("TSOC_INGEST_TOKEN")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))

    def _headers(self) -> Dict[str, str]:
        if not self.ingest_token:
            return {}
        return {"Authorization": "Bearer {0}".format(self.ingest_token)}

    @staticmethod
    def _to_payload(body: Union[ReqModel, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(body, BaseModel):
            return body.model_dump(mode="json")
        return body

    def _raise_api_error(self, exc: httpx.HTTPStatusError) -> None:
        code = exc.response.status_code
        text = exc.response.text or ""
        msg = "TSOC API request failed status={0}".format(code)
        if code in (401, 403):
            raise TsocAuthError(msg + " auth error")
        if code == 404:
            raise TsocNotFoundError(msg + " not found")
        raise TsocApiError(msg, status_code=code, response_text=text)

    async def _post_model(
        self, path: str, body: Union[ReqModel, Dict[str, Any]], out_model: Type[ResModel]
    ) -> ResModel:
        payload = self._to_payload(body)
        url = "{0}{1}".format(self.base_url, path)
        last_timeout_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(url, headers=self._headers(), json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return out_model.model_validate(data)
            except httpx.TimeoutException as e:
                last_timeout_error = e
                if attempt >= self.max_retries:
                    raise TsocTimeoutError("TSOC API timeout after retries") from e
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (500, 502, 503, 504) and attempt < self.max_retries:
                    pass
                else:
                    self._raise_api_error(e)
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_backoff_seconds * (2**attempt))
        if last_timeout_error is not None:
            raise TsocTimeoutError("TSOC API timeout after retries") from last_timeout_error
        raise TsocApiError("TSOC API request failed after retries", status_code=0, response_text="")

    async def _get_raw(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = "{0}{1}".format(self.base_url, path)
        clean: Dict[str, Any] = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=self._headers(), params=clean)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            raise TsocTimeoutError("TSOC API timeout") from e
        except httpx.HTTPStatusError as e:
            self._raise_api_error(e)

    async def _get_model(self, path: str, out_model: Type[ResModel], params: Optional[Dict[str, Any]] = None) -> ResModel:
        data = await self._get_raw(path, params)
        return out_model.model_validate(data)

    async def _post_raw(self, path: str, body: Union[Dict[str, Any], BaseModel]) -> Dict[str, Any]:
        payload = self._to_payload(body)
        url = "{0}{1}".format(self.base_url, path)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            raise TsocTimeoutError("TSOC API timeout") from e
        except httpx.HTTPStatusError as e:
            self._raise_api_error(e)

    # ----- existing endpoints -----

    async def classify_alert(
        self,
        body: Union[AlertClassificationRequest, Dict[str, Any]],
    ) -> AlertClassificationResult:
        return await self._post_model("/api/v1/classification/alert", body, AlertClassificationResult)

    async def route_analysis(
        self,
        body: Union[AnalysisRouteRequest, Dict[str, Any]],
    ) -> AnalysisRouteResponse:
        return await self._post_model("/api/v1/analysis/route", body, AnalysisRouteResponse)

    async def run_agent_triage(
        self,
        body: Union[AgentTriageRequest, Dict[str, Any]],
    ) -> AgentTriageResponse:
        return await self._post_model("/api/v1/agents/triage", body, AgentTriageResponse)

    async def suggest_spl(
        self,
        body: Union[SplAssistantSuggestRequest, Dict[str, Any]],
    ) -> SplAssistantSuggestResponse:
        return await self._post_model("/api/v1/assistant/spl-suggest", body, SplAssistantSuggestResponse)

    async def mcp_status(self) -> Dict[str, Any]:
        """GET /api/v1/mcp/status — Splunk MCP Server connectivity."""
        url = "{0}/api/v1/mcp/status".format(self.base_url)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    # ----- Splunk MCP integration -----

    async def mcp_generate_spl(
        self,
        body: Union[McpSplGenerateRequest, Dict[str, Any]],
    ) -> McpSplGenerateResponse:
        """POST /api/v1/mcp/spl-generate — Generate SPL from natural language via Splunk MCP SAIA."""
        return await self._post_model("/api/v1/mcp/spl-generate", body, McpSplGenerateResponse)

    async def mcp_call_tool(
        self,
        body: Union[McpToolCallRequest, Dict[str, Any]],
    ) -> McpToolCallResponse:
        """POST /api/v1/mcp/tools/call — Invoke any Splunk MCP tool by name."""
        return await self._post_model("/api/v1/mcp/tools/call", body, McpToolCallResponse)

    # ----- Splunk REST analysis -----

    async def run_analysis(
        self,
        body: Union[AnalysisRunRequest, Dict[str, Any]],
    ) -> SocAnalysisResult:
        """POST /api/v1/analysis/run — Run SOC security analysis directly."""
        return await self._post_model("/api/v1/analysis/run", body, SocAnalysisResult)

    async def run_analysis_by_sid(
        self,
        body: Union[AnalysisBatchBySidRequest, Dict[str, Any]],
    ) -> AnalysisBatchBySidResponse:
        """POST /api/v1/analysis/run-by-sid — Fetch Splunk job results by SID via REST and batch-analyze."""
        return await self._post_model("/api/v1/analysis/run-by-sid", body, AnalysisBatchBySidResponse)

    # ----- Storage & dashboard -----

    async def search_events(
        self,
        *,
        sid: Optional[str] = None,
        record_type: Optional[str] = None,
        row_index: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """GET /api/v1/storage/events — Query stored analysis records."""
        return await self._get_raw("/api/v1/storage/events", {
            "sid": sid, "record_type": record_type, "row_index": row_index, "limit": limit,
        })

    async def get_event(self, record_id: int) -> Dict[str, Any]:
        """GET /api/v1/storage/events/{record_id} — Fetch a single stored record by PostgreSQL id."""
        return await self._get_raw("/api/v1/storage/events/{0}".format(record_id))

    async def dashboard_overview(self) -> DashboardOverview:
        """GET /api/v1/dashboard/overview — SOC dashboard KPIs, triage stats, activity timeline."""
        return await self._get_model("/api/v1/dashboard/overview", DashboardOverview)

    # ----- Observability pipeline -----

    async def run_observability(
        self,
        body: Union[ObservabilityRunRequest, Dict[str, Any]],
    ) -> ObservabilityAnalysisResult:
        """POST /api/v1/observability/run — Run Diagnoser + Responder + OpsJudge pipeline."""
        return await self._post_model("/api/v1/observability/run", body, ObservabilityAnalysisResult)

    async def run_observability_by_sid(
        self,
        body: Union[ObservabilityBatchBySidRequest, Dict[str, Any]],
    ) -> ObservabilityBatchBySidResponse:
        """POST /api/v1/observability/run-by-sid — Batch observability analysis by Splunk SID (REST v2)."""
        return await self._post_model("/api/v1/observability/run-by-sid", body, ObservabilityBatchBySidResponse)

    # ----- SOC Chat (RAG) -----

    async def soc_chat(
        self,
        body: Union[SocChatRequest, Dict[str, Any]],
    ) -> SocChatResponse:
        """POST /api/v1/soc/chat — AI-powered investigation chat grounded in Splunk analysis data."""
        return await self._post_model("/api/v1/soc/chat", body, SocChatResponse)

    async def soc_chat_status(self) -> Dict[str, Any]:
        """GET /api/v1/soc/chat/status — RAG backend status (Postgres, Qdrant, document count)."""
        return await self._get_raw("/api/v1/soc/chat/status")

    # ----- Investigation -----

    async def investigation_timeline(self, record_id: int) -> Dict[str, Any]:
        """GET /api/v1/investigation/records/{record_id}/timeline — Chronological investigation steps."""
        return await self._get_raw("/api/v1/investigation/records/{0}/timeline".format(record_id))

    async def analyst_actions(self, record_id: int) -> Dict[str, Any]:
        """GET /api/v1/investigation/records/{record_id}/analyst-actions — Human-in-the-loop action log."""
        return await self._get_raw("/api/v1/investigation/records/{0}/analyst-actions".format(record_id))

    async def add_analyst_action(
        self,
        record_id: int,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """POST /api/v1/investigation/records/{record_id}/analyst-actions — Record acknowledge/escalate."""
        return await self._post_raw("/api/v1/investigation/records/{0}/analyst-actions".format(record_id), body)

    # ----- Triage -----

    async def triage_queue(
        self,
        *,
        track: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """GET /api/v1/triage/queue — Priority-sorted analyst review queue."""
        return await self._get_raw("/api/v1/triage/queue", {"track": track, "limit": limit})

    # ----- Health -----

    async def health(self) -> Dict[str, Any]:
        """GET /api/v1/health — Backend liveness check."""
        return await self._get_raw("/api/v1/health")

