"""Webhook relay service — forwards GitHub events to self-hosted instances."""

import asyncio

import httpx
import structlog

log = structlog.get_logger(__name__)

_RELAY_TIMEOUT = 10.0     # seconds per attempt
_RETRY_DELAYS = [1, 3]    # seconds; 3 attempts total (1 initial + 2 retries)


async def forward_event(
    relay_url: str,
    relay_secret: str,
    event: str,
    payload: dict,
    installation_id: int,
) -> bool:
    """Forward a GitHub webhook event to a self-hosted instance.

    Sends POST {relay_url} with:
      X-GitHub-Event: {event}
      X-Aether-Relay-Secret: {relay_secret}
      Content-Type: application/json
      body: original payload

    Retries up to 2 times on network/5xx errors.
    Returns True if delivered, False if all attempts failed.
    """
    headers = {
        "X-GitHub-Event": event,
        "X-Aether-Relay-Secret": relay_secret,
        "Content-Type": "application/json",
        "User-Agent": "Aether-Relay/1.0",
    }

    attempts = [0.0] + _RETRY_DELAYS  # first attempt is immediate

    for attempt_num, delay in enumerate(attempts):
        if delay:
            await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=_RELAY_TIMEOUT) as client:
                resp = await client.post(relay_url, json=payload, headers=headers)
                if resp.status_code < 500:
                    log.info(
                        "relay_delivered",
                        installation_id=installation_id,
                        relay_url=relay_url,
                        status=resp.status_code,
                        attempt=attempt_num + 1,
                    )
                    return True
                log.warning(
                    "relay_server_error",
                    installation_id=installation_id,
                    relay_url=relay_url,
                    status=resp.status_code,
                    attempt=attempt_num + 1,
                )
        except httpx.RequestError as exc:
            log.warning(
                "relay_request_error",
                installation_id=installation_id,
                relay_url=relay_url,
                error=str(exc),
                attempt=attempt_num + 1,
            )

    log.error(
        "relay_failed_all_attempts",
        installation_id=installation_id,
        relay_url=relay_url,
    )
    return False
