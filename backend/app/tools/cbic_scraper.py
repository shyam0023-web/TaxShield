"""
TaxShield — CBIC Circular Scraper
Scrapes cbic-gst.gov.in for new GST circulars and notifications.
Stores results in kb_staging table with status=UNVERIFIED.

Usage:
    from app.tools.cbic_scraper import scrape_cbic_circulars
    new_count = await scrape_cbic_circulars(db_session)
"""
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kb_staging import KBStaging

logger = logging.getLogger(__name__)

# CBIC circular listing pages
CBIC_CIRCULARS_URL = "https://taxinformation.cbic.gov.in/content-page/explore-notification"
CBIC_BASE_URL = "https://taxinformation.cbic.gov.in"

# Timeout for HTTP requests
HTTP_TIMEOUT = 30.0


async def scrape_cbic_circulars(db: AsyncSession) -> int:
    """
    Scrape CBIC website for new circulars.
    Returns count of new entries added to staging.
    """
    logger.info("Starting CBIC circular scrape...")

    try:
        circulars = await _fetch_circular_list()
        if not circulars:
            logger.warning("No circulars fetched from CBIC website")
            return 0

        new_count = 0
        for circ in circulars:
            # Check if already exists in staging
            existing = await db.execute(
                select(KBStaging).where(KBStaging.circular_id == circ["circular_id"])
            )
            if existing.scalar_one_or_none():
                continue  # Already scraped

            # Create staging entry
            entry = KBStaging(
                circular_id=circ["circular_id"],
                title=circ["title"],
                full_text=circ.get("text", ""),
                sections=circ.get("sections", []),
                source_url=circ.get("url", ""),
                issue_date=circ.get("issue_date"),
                status="UNVERIFIED",
            )
            db.add(entry)
            new_count += 1

        if new_count > 0:
            await db.commit()
            logger.info(f"CBIC scrape complete: {new_count} new circulars staged")
        else:
            logger.info("CBIC scrape complete: no new circulars found")

        return new_count

    except Exception as e:
        logger.error(f"CBIC scrape failed: {e}")
        await db.rollback()
        return 0


async def _fetch_circular_list() -> List[Dict]:
    """Fetch and parse the CBIC circulars listing page."""
    circulars = []

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(CBIC_CIRCULARS_URL)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Parse circular entries from the page
        # CBIC pages typically have table rows or list items with circular info
        rows = soup.select("table tr, .list-group-item, .notification-item")

        for row in rows:
            parsed = _parse_circular_entry(row)
            if parsed:
                circulars.append(parsed)

        # If table parsing didn't work, try a broader approach
        if not circulars:
            circulars = _parse_page_fallback(soup)

        logger.info(f"Fetched {len(circulars)} circulars from CBIC")

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching CBIC circulars: {e}")
    except Exception as e:
        logger.error(f"Error parsing CBIC page: {e}")

    return circulars


def _parse_circular_entry(element) -> Optional[Dict]:
    """Parse a single circular entry from the page HTML."""
    text = element.get_text(strip=True)
    if not text or len(text) < 20:
        return None

    # Try to extract circular number (e.g., "Circular No. 239/33/2024-GST")
    circ_match = re.search(
        r'[Cc]ircular\s+(?:No\.?\s*)?(\d+/\d+/\d{4}(?:-GST)?)',
        text
    )
    if not circ_match:
        # Try notification pattern: "Notification No. 09/2023"
        circ_match = re.search(
            r'[Nn]otification\s+(?:No\.?\s*)?(\d+/\d{4}(?:-\w+)?)',
            text
        )

    if not circ_match:
        return None

    circular_id = circ_match.group(1)

    # Extract date if present
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    issue_date = None
    if date_match:
        try:
            date_str = date_match.group(1)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
                try:
                    issue_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
        except Exception:
            pass

    # Extract sections referenced
    sections = list(set(re.findall(r'[Ss]ection\s+(\d+)', text)))

    # Extract link if present
    link = element.find("a")
    url = ""
    if link and link.get("href"):
        href = link["href"]
        url = href if href.startswith("http") else f"{CBIC_BASE_URL}{href}"

    return {
        "circular_id": f"CBIC-{circular_id}",
        "title": text[:300],
        "text": text,
        "sections": sections,
        "url": url,
        "issue_date": issue_date,
    }


def _parse_page_fallback(soup: BeautifulSoup) -> List[Dict]:
    """Fallback: extract circulars from any links containing 'circular' or 'notification'."""
    circulars = []

    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        if not text:
            continue

        # Check if this is a circular/notification link
        if re.search(r'circular|notification', text, re.IGNORECASE):
            circ_match = re.search(r'(\d+/\d+/\d{4}|\d+/\d{4})', text)
            if circ_match:
                href = link["href"]
                url = href if href.startswith("http") else f"{CBIC_BASE_URL}{href}"

                circulars.append({
                    "circular_id": f"CBIC-{circ_match.group(1)}",
                    "title": text[:300],
                    "text": text,
                    "sections": list(set(re.findall(r'[Ss]ection\s+(\d+)', text))),
                    "url": url,
                    "issue_date": None,
                })

    return circulars


# Manual entry helper — for adding circulars without scraping
async def add_manual_circular(db: AsyncSession, circular_id: str, title: str,
                               full_text: str, sections: List[str],
                               source_url: str = "") -> KBStaging:
    """Add a circular manually to staging (bypasses scraper)."""
    entry = KBStaging(
        circular_id=circular_id,
        title=title,
        full_text=full_text,
        sections=sections,
        source_url=source_url,
        status="UNVERIFIED",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info(f"Manual circular added to staging: {circular_id}")
    return entry
