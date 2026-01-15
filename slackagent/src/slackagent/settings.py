from __future__ import annotations

import json
import os
from dataclasses import dataclass


def _first_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_headers(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Headers JSON must be an object")
    headers: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Headers JSON must contain string values")
        headers[key] = value
    return headers


@dataclass(slots=True)
class Settings:
    slack_bot_token: str
    slack_signing_secret: str
    slack_app_token: str | None
    slack_trigger_emoji: str
    slack_trigger_reaction: str
    slack_agent_ack_reaction: str
    host: str
    port: int

    a2a_agent_url: str
    a2a_headers: dict[str, str]
    a2a_transports: str | None
    a2a_timeout_s: float
    a2a_poll_interval_s: float
    a2a_poll_timeout_s: float | None
    a2a_use_extended_card: bool
    a2a_verify_tls: bool

    @classmethod
    def from_env(cls) -> "Settings":
        slack_bot_token = _first_env("SLACK_BOT_TOKEN")
        slack_signing_secret = _first_env("SLACK_SIGNING_SECRET")
        if not slack_bot_token:
            raise ValueError("SLACK_BOT_TOKEN is required")
        if not slack_signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET is required")

        a2a_url = _first_env("SLACKAGENT_A2A_URL", "KAGENT_A2A_URL")
        if not a2a_url:
            raise ValueError("SLACKAGENT_A2A_URL (or KAGENT_A2A_URL) is required")

        headers_raw = _first_env("SLACKAGENT_A2A_HEADERS_JSON", "KAGENT_A2A_HEADERS_JSON")
        timeout_s = float(_first_env("SLACKAGENT_A2A_TIMEOUT_S", default="600"))
        poll_interval_s = float(_first_env("SLACKAGENT_A2A_POLL_INTERVAL_S", default="0.5"))
        poll_timeout_raw = _first_env("SLACKAGENT_A2A_POLL_TIMEOUT_S")
        poll_timeout_s = float(poll_timeout_raw) if poll_timeout_raw else None

        return cls(
            slack_bot_token=slack_bot_token,
            slack_signing_secret=slack_signing_secret,
            slack_app_token=_first_env("SLACK_APP_TOKEN"),
            slack_trigger_emoji=_first_env("SLACK_TRIGGER_EMOJI", default="slackagent")
            or "slackagent",
            slack_trigger_reaction=_first_env("SLACK_TRIGGER_REACTION", default="eyes") or "eyes",
            slack_agent_ack_reaction=_first_env(
                "SLACK_AGENT_ACK_REACTION", default="white_check_mark"
            )
            or "white_check_mark",
            host=_first_env("HOST", default="0.0.0.0") or "0.0.0.0",
            port=int(_first_env("PORT", default="3000")),
            a2a_agent_url=a2a_url,
            a2a_headers=_parse_headers(headers_raw),
            a2a_transports=_first_env("SLACKAGENT_A2A_TRANSPORTS", "KAGENT_A2A_TRANSPORTS"),
            a2a_timeout_s=timeout_s,
            a2a_poll_interval_s=poll_interval_s,
            a2a_poll_timeout_s=poll_timeout_s,
            a2a_use_extended_card=_parse_bool(
                _first_env("SLACKAGENT_A2A_USE_EXTENDED_CARD", "KAGENT_A2A_USE_EXTENDED_CARD"),
                default=False,
            ),
            a2a_verify_tls=not _parse_bool(
                _first_env("SLACKAGENT_A2A_INSECURE", "KAGENT_A2A_INSECURE"),
                default=False,
            ),
        )
