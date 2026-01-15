from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from slackagent.a2a_client import SlackAgentClient
from slackagent.settings import Settings


def register_handlers(
    app: AsyncApp,
    *,
    settings: Settings,
    agent_client: SlackAgentClient,
) -> None:
    async def _handle_reaction(event: dict[str, Any], body: dict[str, Any], client: AsyncWebClient, logger, context):
        try:
            await _process_reaction(
                event=event,
                body=body,
                client=client,
                logger=logger,
                context=context,
                settings=settings,
                agent_client=agent_client,
            )
        except Exception:
            logger.exception("Failed to process reaction event")

    @app.event("reaction_added")
    async def reaction_added(event, body, client, logger, context):
        _spawn(_handle_reaction(event, body, client, logger, context), logger)


def _spawn(coro: Awaitable[None], logger) -> None:
    task = asyncio.create_task(coro)

    def _done_callback(fut: asyncio.Future) -> None:
        try:
            fut.result()
        except Exception:
            logger.exception("Background task failed")

    task.add_done_callback(_done_callback)


async def _process_reaction(
    *,
    event: dict[str, Any],
    body: dict[str, Any],
    client: AsyncWebClient,
    logger,
    context,
    settings: Settings,
    agent_client: SlackAgentClient,
) -> None:
    reaction = event.get("reaction")
    if reaction != settings.slack_trigger_emoji:
        return

    bot_user_id = context.get("bot_user_id")
    if bot_user_id and event.get("user") == bot_user_id:
        return

    item = event.get("item") or {}
    if item.get("type") != "message":
        return

    channel_id = item.get("channel")
    message_ts = item.get("ts")
    if not channel_id or not message_ts:
        return

    message = await _fetch_message(client, channel_id, message_ts)
    if not message:
        return

    thread_ts = message.get("thread_ts") or message.get("ts")
    if not thread_ts:
        return

    team_id = body.get("team_id") or context.get("team_id") or ""
    thread_key = f"{team_id}:{channel_id}:{thread_ts}"
    context_id = f"slack:{thread_key}"

    await _add_reaction(
        client,
        channel_id=channel_id,
        message_ts=message_ts,
        reaction=settings.slack_trigger_reaction,
        logger=logger,
    )

    message_text = (message.get("text") or "").strip()
    prompt = _render_prompt(
        channel_id=channel_id,
        thread_ts=thread_ts,
        message_ts=message_ts,
        trigger_emoji=settings.slack_trigger_emoji,
        agent_ack_reaction=settings.slack_agent_ack_reaction,
        tagged_message=message_text,
    )
    logger.info(
        "Triggering SlackAgent for thread %s",
        thread_key,
    )

    try:
        await agent_client.ask(
            text=prompt,
            context_id=context_id,
            poll_interval_s=settings.a2a_poll_interval_s,
            poll_timeout_s=settings.a2a_poll_timeout_s,
        )
    except Exception:
        logger.exception("SlackAgent request failed")


async def _fetch_message(client: AsyncWebClient, channel_id: str, message_ts: str) -> dict[str, Any] | None:
    response = await client.conversations_history(
        channel=channel_id,
        latest=message_ts,
        oldest=message_ts,
        inclusive=True,
        limit=1,
    )
    messages = response.get("messages") or []
    return messages[0] if messages else None


def _render_prompt(
    channel_id: str,
    thread_ts: str,
    message_ts: str,
    trigger_emoji: str,
    agent_ack_reaction: str,
    tagged_message: str,
) -> str:
    prompt_text = tagged_message or "Please fix the issue of this thread"
    instructions = [
        "Use slack_get_thread_replies to fetch the full thread, then add new messages to context.",
        f"Add reaction :{agent_ack_reaction}: to the thread root to acknowledge the trigger.",
        "Post your response to the same thread.",
    ]
    meta = [
        f"Channel: {channel_id}",
        f"Thread TS: {thread_ts}",
        f"Reaction message TS: {message_ts}",
        f"Trigger emoji: :{trigger_emoji}:",
    ]
    return "\n".join(
        [
            "Pre-instructions:",
            *instructions,
            "",
            "Metadata:",
            *meta,
            "",
            "Prompt:",
            prompt_text,
        ]
    ).strip()


async def _add_reaction(
    client: AsyncWebClient,
    *,
    channel_id: str,
    message_ts: str,
    reaction: str,
    logger,
) -> None:
    try:
        await client.reactions_add(
            channel=channel_id,
            timestamp=message_ts,
            name=reaction,
        )
    except SlackApiError as exc:
        error_code = exc.response.get("error")
        if error_code not in {"already_reacted"}:
            logger.warning("Failed to add reaction %s: %s", reaction, error_code)
