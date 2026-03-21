"""
TaxShield — Webhook Notifications
Fire webhook callbacks when key events occur (processing complete, draft ready).
"""
import asyncio
import httpx
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Webhooks are configured via env: WEBHOOK_URL
# If not set, webhooks are silently disabled.


async def fire_webhook(event: str, payload: dict) -> bool:
    """
    Fire a webhook notification to the configured URL.
    
    Args:
        event: Event type (e.g., "notice.processed", "draft.approved")
        payload: Event data to send
        
    Returns:
        True if webhook was sent successfully, False otherwise
    """
    webhook_url = getattr(settings, "WEBHOOK_URL", "")
    if not webhook_url:
        return False

    webhook_data = {
        "event": event,
        "data": payload,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=webhook_data)
            if response.status_code < 300:
                logger.info(f"Webhook sent: {event} → {webhook_url} (status={response.status_code})")
                return True
            else:
                logger.warning(f"Webhook failed: {event} → {webhook_url} (status={response.status_code})")
                return False
    except Exception as e:
        logger.error(f"Webhook error: {event} → {e}")
        return False


def fire_webhook_background(event: str, payload: dict) -> None:
    """Fire a webhook in the background (non-blocking)."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(fire_webhook(event, payload))
    except RuntimeError:
        # No event loop running — skip silently
        pass


# ═══════════════════════════════════════════
# Webhook Events
# ═══════════════════════════════════════════

EVENTS = {
    "notice.uploaded": "A new notice was uploaded for processing",
    "notice.processed": "Notice processing completed successfully",
    "notice.error": "Notice processing failed with error",
    "draft.approved": "A draft reply was approved",
    "draft.rejected": "A draft reply was rejected",
    "notice.deleted": "A notice was deleted (DPDP erasure)",
}
