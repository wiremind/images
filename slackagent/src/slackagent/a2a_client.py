from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Iterable
from uuid import uuid4

import httpx

from a2a.client import Client, ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    Artifact,
    DataPart,
    FilePart,
    FileWithBytes,
    FileWithUri,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskQueryParams,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
    TransportProtocol,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH, PREV_AGENT_CARD_WELL_KNOWN_PATH


def _part_to_text(part: Part) -> str:
    payload = part.root
    if isinstance(payload, TextPart):
        return payload.text
    if isinstance(payload, DataPart):
        return json.dumps(payload.data, ensure_ascii=False, indent=2, sort_keys=True)
    if isinstance(payload, FilePart):
        file_obj = payload.file
        label = file_obj.name or "file"
        mime = f" ({file_obj.mime_type})" if file_obj.mime_type else ""
        if isinstance(file_obj, FileWithUri):
            return f"[{label}{mime}: {file_obj.uri}]"
        if isinstance(file_obj, FileWithBytes):
            return f"[{label}{mime}: {len(file_obj.bytes)} base64 chars]"
    return f"[unsupported part: {type(payload).__name__}]"


def _message_to_text(message: Message) -> str:
    return "\n".join(_part_to_text(part) for part in message.parts).strip()


def _artifact_to_text(artifact: Artifact) -> str:
    return "\n".join(_part_to_text(part) for part in artifact.parts).strip()


def _task_to_text(task: Task) -> str:
    if task.artifacts:
        rendered = "\n".join(
            _artifact_to_text(artifact) for artifact in task.artifacts if artifact.parts
        ).strip()
        if rendered:
            return rendered
    if task.status.message:
        rendered = _message_to_text(task.status.message)
        if rendered:
            return rendered
    if task.history:
        for message in reversed(task.history):
            if message.role == Role.agent:
                rendered = _message_to_text(message)
                if rendered:
                    return rendered
    return ""


def _build_message(text: str, *, context_id: str | None) -> Message:
    return Message(
        role=Role.user,
        parts=[Part(TextPart(text=text))],
        message_id=str(uuid4()),
        context_id=context_id,
    )


def _parse_transports(raw: str | None) -> list[TransportProtocol]:
    if not raw:
        return [TransportProtocol.jsonrpc, TransportProtocol.http_json]
    mapping: dict[str, TransportProtocol] = {
        "jsonrpc": TransportProtocol.jsonrpc,
        "json-rpc": TransportProtocol.jsonrpc,
        "http+json": TransportProtocol.http_json,
        "http-json": TransportProtocol.http_json,
        "rest": TransportProtocol.http_json,
        "grpc": TransportProtocol.grpc,
    }
    protocols: list[TransportProtocol] = []
    for item in raw.split(","):
        key = item.strip().lower()
        if not key:
            continue
        if key not in mapping:
            raise ValueError(f"Unknown transport: {item!r}")
        protocols.append(mapping[key])
    return protocols or [TransportProtocol.jsonrpc, TransportProtocol.http_json]


async def _fetch_agent_card(http: httpx.AsyncClient, *, agent_url: str) -> AgentCard:
    base = agent_url.rstrip("/")
    for suffix in (AGENT_CARD_WELL_KNOWN_PATH, PREV_AGENT_CARD_WELL_KNOWN_PATH, "/v1/card"):
        url = base + suffix
        try:
            response = await http.get(url)
            response.raise_for_status()
            return AgentCard.model_validate(response.json())
        except Exception:
            continue
    raise RuntimeError("Unable to fetch AgentCard from the provided A2A URL")


@dataclass(slots=True)
class _ArtifactCollector:
    _order: list[str] = field(default_factory=list)
    _text_by_id: dict[str, str] = field(default_factory=dict)

    def add(self, update: TaskArtifactUpdateEvent) -> None:
        artifact_id = update.artifact.artifact_id
        chunk = _artifact_to_text(update.artifact)
        previous = self._text_by_id.get(artifact_id, "")
        if artifact_id not in self._text_by_id:
            self._order.append(artifact_id)
        if update.append:
            self._text_by_id[artifact_id] = previous + chunk
        else:
            self._text_by_id[artifact_id] = chunk

    def combined(self) -> str:
        return "\n".join(self._text_by_id[artifact_id] for artifact_id in self._order).strip()


@dataclass(slots=True)
class SlackAgentClient:
    agent_url: str
    headers: dict[str, str]
    transports_raw: str | None
    timeout_s: float
    use_extended_card: bool
    verify_tls: bool

    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _http: httpx.AsyncClient | None = field(default=None, init=False)
    _client: Client | None = field(default=None, init=False)
    _card: AgentCard | None = field(default=None, init=False)

    async def _ensure(self) -> tuple[Client, AgentCard]:
        async with self._lock:
            if self._client is not None and self._card is not None and self._http is not None:
                return self._client, self._card

            timeout = httpx.Timeout(self.timeout_s, connect=self.timeout_s, read=None)
            self._http = httpx.AsyncClient(
                timeout=timeout,
                headers=self.headers or None,
                verify=self.verify_tls,
            )

            public_card = await _fetch_agent_card(self._http, agent_url=self.agent_url)
            client_card = public_card
            if not self.use_extended_card:
                client_card = public_card.model_copy(
                    update={"supports_authenticated_extended_card": False}
                )

            factory = ClientFactory(
                ClientConfig(
                    streaming=True,
                    polling=False,
                    httpx_client=self._http,
                    supported_transports=_parse_transports(self.transports_raw),
                )
            )
            client = factory.create(client_card)
            if self.use_extended_card:
                public_card = await client.get_card()

            self._client = client
            self._card = public_card
            return client, public_card

    async def ask(
        self,
        *,
        text: str,
        context_id: str | None,
        poll_interval_s: float,
        poll_timeout_s: float | None,
    ) -> tuple[str, str | None]:
        client, _ = await self._ensure()
        message = _build_message(text, context_id=context_id)
        collector = _ArtifactCollector()

        last_task: Task | None = None
        final_message: Message | None = None
        context_out: str | None = context_id

        async for event in client.send_message(message):
            if isinstance(event, Message):
                final_message = event
                context_out = event.context_id
                break

            task, update = event
            last_task = task
            context_out = task.context_id

            if isinstance(update, TaskArtifactUpdateEvent):
                collector.add(update)
            if isinstance(update, TaskStatusUpdateEvent) and update.final:
                break

        if final_message is not None:
            return _message_to_text(final_message) or "(no response text)", context_out

        if last_task is None:
            return "(no response)", context_out

        if last_task.status.state in {TaskState.submitted, TaskState.working}:
            last_task = await self._poll_task(
                client,
                last_task,
                poll_interval_s=poll_interval_s,
                poll_timeout_s=poll_timeout_s,
            )

        text_out = collector.combined() or _task_to_text(last_task) or "(no response text)"
        return text_out, context_out

    async def _poll_task(
        self,
        client: Client,
        task: Task,
        *,
        poll_interval_s: float,
        poll_timeout_s: float | None,
    ) -> Task:
        loop = asyncio.get_running_loop()
        deadline = None if poll_timeout_s is None else (loop.time() + poll_timeout_s)
        current = task
        while current.status.state in {TaskState.submitted, TaskState.working}:
            if deadline is not None and loop.time() >= deadline:
                return current
            await asyncio.sleep(poll_interval_s)
            current = await client.get_task(TaskQueryParams(id=current.id, history_length=None))
        return current


def create_slackagent_client(
    *,
    agent_url: str,
    headers: dict[str, str],
    transports_raw: str | None,
    timeout_s: float,
    use_extended_card: bool,
    verify_tls: bool,
) -> SlackAgentClient:
    return SlackAgentClient(
        agent_url=agent_url,
        headers=headers,
        transports_raw=transports_raw,
        timeout_s=timeout_s,
        use_extended_card=use_extended_card,
        verify_tls=verify_tls,
    )
