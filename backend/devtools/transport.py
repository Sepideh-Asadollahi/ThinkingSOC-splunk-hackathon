"""HTTP transport helpers shared by sync/async SDK clients."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import httpx
from pydantic import BaseModel

from .errors import TsocApiError, TsocAuthError, TsocNotFoundError, TsocTimeoutError

ResModel = TypeVar("ResModel", bound=BaseModel)


def raise_api_error(exc: httpx.HTTPStatusError) -> None:
    code = exc.response.status_code
    text = exc.response.text or ""
    msg = "TSOC API request failed status={0}".format(code)
    if code in (401, 403):
        raise TsocAuthError(msg + " auth error")
    if code == 404:
        raise TsocNotFoundError(msg + " not found")
    raise TsocApiError(msg, status_code=code, response_text=text)


def to_payload(body: Union[BaseModel, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(body, BaseModel):
        return body.model_dump(mode="json")
    return body


def get_json_list(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
    out_model: Type[ResModel],
    params: Optional[Dict[str, Any]] = None,
) -> List[ResModel]:
    clean: Dict[str, Any] = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url, headers=headers, params=clean)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)
    if not isinstance(data, list):
        raise TsocApiError("Expected JSON list response", status_code=200, response_text=str(data)[:500])
    return [out_model.model_validate(item) for item in data]


def patch_json_model(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
    body: Union[BaseModel, Dict[str, Any]],
    out_model: Type[ResModel],
) -> ResModel:
    payload = to_payload(body)
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            return out_model.model_validate(response.json())
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)


def delete_no_content(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
) -> None:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.delete(url, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)


def delete_json(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.delete(url, headers=headers)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {"ok": True}
            data = response.json()
            return data if isinstance(data, dict) else {"ok": True, "result": data}
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)


async def async_get_json_list(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
    out_model: Type[ResModel],
    params: Optional[Dict[str, Any]] = None,
) -> List[ResModel]:
    clean: Dict[str, Any] = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers, params=clean)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)
    if not isinstance(data, list):
        raise TsocApiError("Expected JSON list response", status_code=200, response_text=str(data)[:500])
    return [out_model.model_validate(item) for item in data]


async def async_patch_json_model(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
    body: Union[BaseModel, Dict[str, Any]],
    out_model: Type[ResModel],
) -> ResModel:
    payload = to_payload(body)
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            return out_model.model_validate(response.json())
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)


async def async_delete_no_content(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
) -> None:
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)


async def async_delete_json(
    *,
    url: str,
    headers: Dict[str, str],
    timeout_seconds: float,
) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {"ok": True}
            data = response.json()
            return data if isinstance(data, dict) else {"ok": True, "result": data}
    except httpx.TimeoutException as e:
        raise TsocTimeoutError("TSOC API timeout") from e
    except httpx.HTTPStatusError as e:
        raise_api_error(e)
