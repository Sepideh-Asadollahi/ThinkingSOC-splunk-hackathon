"""Typed async SDK client for ThinkingSOC Lite backend APIs."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import httpx
from pydantic import BaseModel

from models.admin_org import AdminOrgGapSuggestRequest, AdminOrgGapSuggestResponse
from models.agentic_ops import AlertClassificationRequest, AlertClassificationResult, AnalysisRouteRequest, AnalysisRouteResponse
from models.agents import AgentTriageRequest, AgentTriageResponse
from models.analysis import AnalysisBatchBySidRequest, AnalysisBatchBySidResponse, AnalysisRunRequest, SocAnalysisResult
from models.assistant import SplAssistantSuggestRequest, SplAssistantSuggestResponse
from models.dashboard import DashboardOverview
from models.enrichment import EnrichRequest, EnrichmentResult
from models.handoff import SplunkAlertIngest
from models.integration_settings import IntegrationSettingCreate, IntegrationSettingRecord, IntegrationSettingUpdate
from models.inventory import (
    AssetCreate,
    AssetRecord,
    AssetUpdate,
    RelationshipCreate,
    RelationshipRecord,
    RelationshipUpdate,
    UserCreate,
    UserRecord,
    UserUpdate,
)
from models.mcp import McpSplGenerateRequest, McpSplGenerateResponse, McpToolCallRequest, McpToolCallResponse
from models.observability import (
    ObservabilityAnalysisResult,
    ObservabilityBatchBySidRequest,
    ObservabilityBatchBySidResponse,
    ObservabilityRunRequest,
)
from models.runbook import (
    RunbookApproval,
    RunbookApprovalBody,
    RunbookCompatibleTargets,
    RunbookExportBundle,
    RunbookImportBody,
    RunbookImportResponse,
    RunbookLibraryResponse,
    RunbookRevisionBody,
    RunbookRun,
    RunbookRunBody,
    RunbookRuntimeStatus,
    VerifiedRunbookDraft,
    VerifiedRunbookState,
)
from services.soc_rag.models import (
    SocChatConversationDetail,
    SocChatConversationSummary,
    SocChatCreateConversationRequest,
    SocChatRequest,
    SocChatResponse,
)

from .errors import TsocApiError, TsocAuthError, TsocNotFoundError, TsocSdkError, TsocTimeoutError
from .transport import async_delete_json, async_delete_no_content, async_get_json_list, async_patch_json_model
from .workflows import build_doctor_report, build_full_investigation_result

ReqModel = Union[
    AlertClassificationRequest,
    AnalysisRouteRequest,
    AgentTriageRequest,
    SplAssistantSuggestRequest,
    RunbookApprovalBody,
    RunbookRunBody,
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

    async def mcp_run_query(
        self,
        search_query: str,
        *,
        extra_arguments: Optional[Dict[str, Any]] = None,
    ) -> McpToolCallResponse:
        """Run SPL via Splunk MCP ``splunk_run_query``."""
        arguments: Dict[str, Any] = {"search_query": search_query}
        if extra_arguments:
            arguments.update(extra_arguments)
        return await self.mcp_call_tool({"tool_name": "splunk_run_query", "arguments": arguments})

    async def mcp_saia_ask(
        self,
        question: str,
        *,
        additional_context: Optional[str] = None,
    ) -> McpToolCallResponse:
        """Ask Splunk SAIA via MCP ``saia_ask_splunk_question``."""
        arguments: Dict[str, Any] = {"prompt": question}
        if additional_context is not None:
            arguments["additional_context"] = additional_context
        return await self.mcp_call_tool({"tool_name": "saia_ask_splunk_question", "arguments": arguments})

    # ----- Webhook ingest -----

    async def ingest_alert(
        self,
        body: Union[SplunkAlertIngest, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """POST /api/v1/alerts/splunk-ingest — Splunk alert action webhook (requires Bearer token)."""
        return await self._post_raw("/api/v1/alerts/splunk-ingest", body)

    # ----- LLM status -----

    async def llm_status(self) -> Dict[str, Any]:
        """GET /api/v1/llm/status — LiteLLM configuration (no secrets returned)."""
        return await self._get_raw("/api/v1/llm/status")

    async def doctor(self) -> Dict[str, Any]:
        """Connectivity check: health + MCP + LLM + SOC chat + graph + inventory."""
        graph_health: Optional[Dict[str, Any]] = None
        inventory_status: Optional[Dict[str, Any]] = None
        try:
            graph_health = await self.graph_health()
        except TsocSdkError:
            graph_health = {"status": "unavailable"}
        try:
            inventory_status = await self.inventory_status()
        except TsocSdkError:
            inventory_status = {"postgres_configured": False}
        return build_doctor_report(
            health=await self.health(),
            mcp_status=await self.mcp_status(),
            llm_status=await self.llm_status(),
            soc_chat_status=await self.soc_chat_status(),
            graph_health=graph_health,
            inventory_status=inventory_status,
        )

    async def run_full_investigation(
        self,
        body: Union[AgentTriageRequest, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Chain classify → triage → SPL suggest → MCP status for demo/CI."""
        payload = self._to_payload(body)
        classification = await self.classify_alert(payload)
        triage = await self.run_agent_triage(payload)
        spl_body = {
            "search_name": payload.get("search_name"),
            "normalized": payload.get("normalized") or {},
            "objective": payload.get("operator_goal") or "collect root cause evidence",
        }
        spl = await self.suggest_spl(spl_body)
        mcp = await self.mcp_status()
        return build_full_investigation_result(
            classification=classification,
            triage=triage,
            spl=spl,
            mcp_status=mcp,
        )

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

    async def list_soc_chat_conversations(
        self,
        *,
        limit: Optional[int] = None,
    ) -> List[SocChatConversationSummary]:
        """GET /api/v1/soc/chat/conversations — List stored chat sessions."""
        return await async_get_json_list(
            url="{0}/api/v1/soc/chat/conversations".format(self.base_url),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            out_model=SocChatConversationSummary,
            params={"limit": limit},
        )

    async def create_soc_chat_conversation(
        self,
        body: Union[SocChatCreateConversationRequest, Dict[str, Any], None] = None,
    ) -> SocChatConversationSummary:
        """POST /api/v1/soc/chat/conversations — Create a new chat session."""
        payload = self._to_payload(body or {})
        return await self._post_model("/api/v1/soc/chat/conversations", payload, SocChatConversationSummary)

    async def get_soc_chat_conversation(self, conversation_id: str) -> SocChatConversationDetail:
        """GET /api/v1/soc/chat/conversations/{id} — Fetch conversation with messages."""
        return await self._get_model(
            "/api/v1/soc/chat/conversations/{0}".format(conversation_id),
            SocChatConversationDetail,
        )

    async def delete_soc_chat_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """DELETE /api/v1/soc/chat/conversations/{id} — Remove a chat session."""
        return await async_delete_json(
            url="{0}/api/v1/soc/chat/conversations/{1}".format(self.base_url, conversation_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
        )

    async def gap_suggest(
        self,
        body: Union[AdminOrgGapSuggestRequest, Dict[str, Any]],
    ) -> AdminOrgGapSuggestResponse:
        """POST /api/v1/admin-org/gap-suggest — Suggest organizational knowledge gap question."""
        return await self._post_model("/api/v1/admin-org/gap-suggest", body, AdminOrgGapSuggestResponse)

    async def inventory_status(self) -> Dict[str, Any]:
        """GET /api/v1/inventory/status — PostgreSQL inventory backend status."""
        return await self._get_raw("/api/v1/inventory/status")

    async def list_inventory_users(self) -> List[UserRecord]:
        return await async_get_json_list(
            url="{0}/api/v1/inventory/users".format(self.base_url),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            out_model=UserRecord,
        )

    async def create_inventory_user(self, body: Union[UserCreate, Dict[str, Any]]) -> UserRecord:
        return await self._post_model("/api/v1/inventory/users", body, UserRecord)

    async def get_inventory_user(self, user_id: str) -> UserRecord:
        return await self._get_model("/api/v1/inventory/users/{0}".format(user_id), UserRecord)

    async def update_inventory_user(
        self,
        user_id: str,
        body: Union[UserUpdate, Dict[str, Any]],
    ) -> UserRecord:
        return await async_patch_json_model(
            url="{0}/api/v1/inventory/users/{1}".format(self.base_url, user_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            body=body,
            out_model=UserRecord,
        )

    async def delete_inventory_user(self, user_id: str) -> None:
        await async_delete_no_content(
            url="{0}/api/v1/inventory/users/{1}".format(self.base_url, user_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
        )

    async def list_inventory_assets(self) -> List[AssetRecord]:
        return await async_get_json_list(
            url="{0}/api/v1/inventory/assets".format(self.base_url),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            out_model=AssetRecord,
        )

    async def create_inventory_asset(self, body: Union[AssetCreate, Dict[str, Any]]) -> AssetRecord:
        return await self._post_model("/api/v1/inventory/assets", body, AssetRecord)

    async def get_inventory_asset(self, asset_id: str) -> AssetRecord:
        return await self._get_model("/api/v1/inventory/assets/{0}".format(asset_id), AssetRecord)

    async def update_inventory_asset(
        self,
        asset_id: str,
        body: Union[AssetUpdate, Dict[str, Any]],
    ) -> AssetRecord:
        return await async_patch_json_model(
            url="{0}/api/v1/inventory/assets/{1}".format(self.base_url, asset_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            body=body,
            out_model=AssetRecord,
        )

    async def delete_inventory_asset(self, asset_id: str) -> None:
        await async_delete_no_content(
            url="{0}/api/v1/inventory/assets/{1}".format(self.base_url, asset_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
        )

    async def list_inventory_relationships(self) -> List[RelationshipRecord]:
        return await async_get_json_list(
            url="{0}/api/v1/inventory/relationships".format(self.base_url),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            out_model=RelationshipRecord,
        )

    async def create_inventory_relationship(
        self,
        body: Union[RelationshipCreate, Dict[str, Any]],
    ) -> RelationshipRecord:
        return await self._post_model("/api/v1/inventory/relationships", body, RelationshipRecord)

    async def get_inventory_relationship(self, relationship_id: str) -> RelationshipRecord:
        return await self._get_model(
            "/api/v1/inventory/relationships/{0}".format(relationship_id),
            RelationshipRecord,
        )

    async def update_inventory_relationship(
        self,
        relationship_id: str,
        body: Union[RelationshipUpdate, Dict[str, Any]],
    ) -> RelationshipRecord:
        return await async_patch_json_model(
            url="{0}/api/v1/inventory/relationships/{1}".format(self.base_url, relationship_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            body=body,
            out_model=RelationshipRecord,
        )

    async def delete_inventory_relationship(self, relationship_id: str) -> None:
        await async_delete_no_content(
            url="{0}/api/v1/inventory/relationships/{1}".format(self.base_url, relationship_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
        )

    async def enrich_inventory(
        self,
        body: Union[EnrichRequest, Dict[str, Any]],
    ) -> EnrichmentResult:
        return await self._post_model("/api/v1/inventory/enrich", body, EnrichmentResult)

    async def list_integrations(self) -> List[IntegrationSettingRecord]:
        return await async_get_json_list(
            url="{0}/api/v1/integrations/settings".format(self.base_url),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            out_model=IntegrationSettingRecord,
        )

    async def get_integration(self, setting_id: str) -> IntegrationSettingRecord:
        return await self._get_model(
            "/api/v1/integrations/settings/{0}".format(setting_id),
            IntegrationSettingRecord,
        )

    async def create_integration(
        self,
        body: Union[IntegrationSettingCreate, Dict[str, Any]],
    ) -> IntegrationSettingRecord:
        return await self._post_model("/api/v1/integrations/settings", body, IntegrationSettingRecord)

    async def update_integration(
        self,
        setting_id: str,
        body: Union[IntegrationSettingUpdate, Dict[str, Any]],
    ) -> IntegrationSettingRecord:
        return await async_patch_json_model(
            url="{0}/api/v1/integrations/settings/{1}".format(self.base_url, setting_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            body=body,
            out_model=IntegrationSettingRecord,
        )

    async def delete_integration(self, setting_id: str) -> None:
        await async_delete_no_content(
            url="{0}/api/v1/integrations/settings/{1}".format(self.base_url, setting_id),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
        )

    async def graph_health(self) -> Dict[str, Any]:
        return await self._get_raw("/api/v1/graph/health")

    async def graph_findings(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        finding_type: Optional[str] = None,
        exclude_finding_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._get_raw("/api/v1/graph/findings", {
            "limit": limit,
            "offset": offset,
            "finding_type": finding_type,
            "exclude_finding_type": exclude_finding_type,
        })

    async def graph_get_finding(self, finding_id: str) -> Dict[str, Any]:
        return await self._get_raw("/api/v1/graph/findings/{0}".format(finding_id))

    async def graph_finding_graph_data(self, finding_id: str) -> Dict[str, Any]:
        return await self._get_raw("/api/v1/graph/findings/{0}/graph-data".format(finding_id))

    async def graph_topology(self, identifier: str) -> Dict[str, Any]:
        return await self._get_raw("/api/v1/graph/topology/{0}".format(identifier))

    async def graph_attack_tree(self, identifier: str) -> Dict[str, Any]:
        return await self._get_raw("/api/v1/graph/attack-tree/{0}".format(identifier))

    async def graph_discover_attack_paths(self, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._post_raw("/api/v1/graph/analysis/discover-attack-paths", body or {})

    async def graph_operation_status(self, operation_id: str) -> Dict[str, Any]:
        return await self._get_raw("/api/v1/graph/analysis/operations/{0}/status".format(operation_id))

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

    async def runbook_runtime_status(self) -> RunbookRuntimeStatus:
        """GET non-secret ThinkingSOC Lite policy and dependency readiness."""
        return await self._get_model(
            "/api/v1/investigation/runbook-settings",
            RunbookRuntimeStatus,
        )

    async def compatible_runbook_targets(
        self,
        record_id: int,
        *,
        limit: int = 12,
    ) -> RunbookCompatibleTargets:
        """GET minimal exact-detection candidates for guided runbook reuse."""
        payload = await self._get_raw(
            "/api/v1/investigation/records/{0}/runbook/compatible-targets".format(
                record_id
            ),
            {"limit": limit},
        )
        return RunbookCompatibleTargets.model_validate(payload)

    async def runbook_library(
        self, *, search_name: Optional[str] = None
    ) -> RunbookLibraryResponse:
        """GET every immutable runbook revision grouped by exact Alert Name."""
        payload = await self._get_raw(
            "/api/v1/investigation/runbooks",
            {"search_name": search_name},
        )
        return RunbookLibraryResponse.model_validate(payload)

    async def export_runbooks(
        self,
        *,
        runbook_id: Optional[str] = None,
        search_name: Optional[str] = None,
    ) -> RunbookExportBundle:
        """GET the evidence-free v1 portable runbook bundle."""
        payload = await self._get_raw(
            "/api/v1/investigation/runbooks/export",
            {"runbook_id": runbook_id, "search_name": search_name},
        )
        return RunbookExportBundle.model_validate(payload)

    async def import_runbooks(
        self, body: Union[RunbookImportBody, Dict[str, Any]]
    ) -> RunbookImportResponse:
        """POST a portable bundle as inert or freshly verified local drafts."""
        return await self._post_model(
            "/api/v1/investigation/runbooks/import",
            body,
            RunbookImportResponse,
        )

    async def revise_runbook(
        self,
        runbook_id: str,
        body: Union[RunbookRevisionBody, Dict[str, Any]],
    ) -> VerifiedRunbookDraft:
        """PATCH complete content into a new immutable revision."""
        return await async_patch_json_model(
            url="{0}/api/v1/investigation/runbooks/{1}".format(
                self.base_url, runbook_id
            ),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
            body=body,
            out_model=VerifiedRunbookDraft,
        )

    async def verified_runbook_state(self, record_id: int) -> VerifiedRunbookState:
        return await self._get_model(
            "/api/v1/investigation/records/{0}/runbook".format(record_id),
            VerifiedRunbookState,
        )

    async def build_verified_runbook(self, record_id: int) -> VerifiedRunbookDraft:
        return await self._post_model(
            "/api/v1/investigation/records/{0}/runbook".format(record_id),
            {},
            VerifiedRunbookDraft,
        )

    async def decide_verified_runbook(
        self,
        record_id: int,
        body: Union[RunbookApprovalBody, Dict[str, Any]],
    ) -> RunbookApproval:
        return await self._post_model(
            "/api/v1/investigation/records/{0}/runbook/approval".format(record_id),
            body,
            RunbookApproval,
        )

    async def run_verified_runbook(
        self,
        target_record_id: int,
        body: Union[RunbookRunBody, Dict[str, Any]],
    ) -> RunbookRun:
        return await self._post_model(
            "/api/v1/investigation/records/{0}/runbook-runs".format(target_record_id),
            body,
            RunbookRun,
        )

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
