"""API models for integration / connection settings (Splunk, LLM, MCP, etc.)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


SettingCategory = Literal[
    "splunk_rest",
    "splunk_mcp",
    "litellm",
    "postgres",
    "virustotal",
    "ingest",
    "analysis",
    "custom",
]


class IntegrationSettingRecord(BaseModel):
    id: str = Field(description="Stable row id (builtin field name or custom slug).")
    category: SettingCategory
    key: str = Field(description="Display name / env var label.")
    value: str = Field(description="Current value (secrets may be masked).")
    description: Optional[str] = None
    is_secret: bool = False
    builtin: bool = True
    env_var: Optional[str] = None
    configured: bool = True


class IntegrationSettingCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_]*$")
    category: SettingCategory = "custom"
    key: str = Field(min_length=1, max_length=256)
    value: str = ""
    description: Optional[str] = None
    is_secret: bool = False


class IntegrationSettingUpdate(BaseModel):
    category: Optional[SettingCategory] = None
    key: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    is_secret: Optional[bool] = None
