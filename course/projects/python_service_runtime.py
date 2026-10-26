"""Day16 learner workspace: build a Python service, not a completed example.

Read course/tasks/python_service_delivery.md. Add your request/response schemas,
trusted identity dependency, adapters, launcher and tests in your own modules.
Importing this file must not connect to a model, database or external service.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import AsyncContextManager, Protocol

from fastapi import FastAPI


@dataclass(frozen=True)
class ServiceSettings:
    """Validate values in load_settings; annotations alone do not validate them."""

    model_base_url: str
    model_name: str
    model_api_key: str = field(repr=False)
    database_url: str = field(repr=False)
    request_timeout_seconds: float
    max_inflight_requests: int


class ServiceResources(Protocol):
    """Host-owned resources; implementations must enforce identity and I/O limits."""

    async def readiness(self, *, timeout_seconds: float) -> dict:
        """Return dependency readiness; do not generate paid model output."""
        ...

    async def handle(self, payload: dict, *, trusted_principal: str) -> dict:
        """Operate with server-derived identity, never one from model text."""
        ...


class ResourceFactory(Protocol):
    def __call__(self, settings: ServiceSettings) -> AsyncContextManager[ServiceResources]:
        """Acquire resources on enter and release even after partial startup failure."""
        ...


def load_settings(environment: Mapping[str, str]) -> ServiceSettings:
    """Parse explicit configuration, reject invalid values, never expose secrets."""
    raise NotImplementedError("Day16：本人配置装配尚未实现")


def create_app(settings: ServiceSettings, resource_factory: ResourceFactory) -> FastAPI:
    """Build API/contracts/lifespan; creating the app itself must perform no I/O.

    Provide live/ready endpoints and a validated business API. Add a separate
    launcher that constructs settings and your real factory; tests inject fakes.
    """
    raise NotImplementedError("Day16：本人Python服务尚未实现")
