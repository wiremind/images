from __future__ import annotations

import logging
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.aiohttp import AsyncSlackRequestHandler
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from slackagent.a2a_client import create_slackagent_client
from slackagent.settings import Settings
from slackagent.slack_handlers import register_handlers


def _build_slack_app(settings: Settings) -> AsyncApp:
    slack_app = AsyncApp(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )

    agent_client = create_slackagent_client(
        agent_url=settings.a2a_agent_url,
        headers=settings.a2a_headers,
        transports_raw=settings.a2a_transports,
        timeout_s=settings.a2a_timeout_s,
        use_extended_card=settings.a2a_use_extended_card,
        verify_tls=settings.a2a_verify_tls,
    )

    register_handlers(slack_app, settings=settings, agent_client=agent_client)
    return slack_app


async def _build_http_app(settings: Settings) -> web.Application:
    slack_app = _build_slack_app(settings)
    handler = AsyncSlackRequestHandler(slack_app)

    app = web.Application()

    async def healthcheck(_: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_post("/slack/events", handler.handle)
    app.router.add_get("/healthz", healthcheck)

    return app


async def _run_socket_mode(settings: Settings) -> None:
    if not settings.slack_app_token:
        raise ValueError("SLACK_APP_TOKEN is required for socket mode")
    slack_app = _build_slack_app(settings)
    handler = AsyncSocketModeHandler(slack_app, settings.slack_app_token)
    await handler.start_async()


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    settings = Settings.from_env()
    logging.info("Starting SlackAgent bot")

    if settings.slack_app_token:
        asyncio.run(_run_socket_mode(settings))
    else:
        web.run_app(
            _build_http_app(settings),
            host=settings.host,
            port=settings.port,
        )


if __name__ == "__main__":
    main()
