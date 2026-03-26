"""
TaxShield — CBIC Circular Scraper (v2)
Fetches GST circulars from CBIC and stages them for CA review.

Strategy:
  1. Primary: CBIC website with SSL bypass (Indian gov sites have cert issues)
  2. Fallback: Manual entry via API (POST /api/kb/manual)

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

# CBIC sources — try multiple endpoints
CBIC_SOURCES = [
    "https://taxinformation.cbic.gov.in/content-page/explore-notification",
    "https://www.cbic.gov.in/htdocs-cbec/gst/cgst-circulars",
]
CBIC_BASE_URL = "https://taxinformation.cbic.gov.in"
HTTP_TIMEOUT = 30.0


async def scrape_cbic_circulars(db: AsyncSession) -> int:
    """Scrape CBIC website for new circulars. Returns count of new entries."""
    logger.info("Starting CBIC circular scrape...")

    try:
        circulars = await _fetch_circular_list()
        if not circulars:
            logger.warning("No circulars fetched from CBIC")
            return 0

        new_count = 0
        for circ in circulars:
            existing = await db.execute(
                select(KBStaging).where(KBStaging.circular_id == circ["circular_id"])
            )
            if existing.scalar_one_or_none():
                continue

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
            logger.info(f"CBIC scrape: {new_count} new circulars staged")
        else:
            logger.info("CBIC scrape: no new circulars")

        return new_count

    except Exception as e:
        logger.error(f"CBIC scrape failed: {e}")
        await db.rollback()
        return 0


async def _fetch_circular_list() -> List[Dict]:
    """Fetch and parse circulars from multiple CBIC sources."""
    circulars = []

    for source_url in CBIC_SOURCES:
        try:
            # SSL verify=False for Indian gov sites with certificate issues
            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT, follow_redirects=True, verify=False
            ) as client:
                response = await client.get(source_url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Strategy 1: Parse table rows
            rows = soup.select("table tr, .list-group-item, .notification-item, .view-content .views-row")
            for row in rows:
                parsed = _parse_circular_entry(row, source_url)
                if parsed:
                    circulars.append(parsed)

            # Strategy 2: Parse all links with circular/notification patterns
            if not circulars:
                circulars = _parse_all_links(soup, source_url)

            if circulars:
                logger.info(f"Fetched {len(circulars)} circulars from {source_url}")
                break  # Got results, stop trying other sources

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error from {source_url}: {e}")
        except Exception as e:
            logger.warning(f"Error parsing {source_url}: {e}")

    return circulars


def _parse_circular_entry(element, source_url: str) -> Optional[Dict]:
    """Parse a single circular entry from HTML."""
    text = element.get_text(strip=True)
    if not text or len(text) < 20:
        return None

    # Try circular number patterns
    circ_match = re.search(
        r'[Cc]ircular\s+(?:No\.?\s*)?(\d+/\d+/\d{4}(?:-GST)?)', text
    )
    if not circ_match:
        circ_match = re.search(
            r'[Nn]otification\s+(?:No\.?\s*)?(\d+/\d{4}(?:-\w+)?)', text
        )
    if not circ_match:
        return None

    circular_id = circ_match.group(1)

    # Extract date
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    issue_date = None
    if date_match:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y"):
            try:
                issue_date = datetime.strptime(date_match.group(1), fmt)
                break
            except ValueError:
                continue

    sections = list(set(re.findall(r'[Ss]ection\s+(\d+)', text)))

    link = element.find("a")
    url = ""
    if link and link.get("href"):
        href = link["href"]
        if href.startswith("http"):
            url = href
        elif href.startswith("/"):
            from urllib.parse import urlparse
            base = urlparse(source_url)
            url = f"{base.scheme}://{base.netloc}{href}"
        else:
            url = f"{source_url.rsplit('/', 1)[0]}/{href}"

    return {
        "circular_id": f"CBIC-{circular_id}",
        "title": text[:300],
        "text": text,
        "sections": sections,
        "url": url,
        "issue_date": issue_date,
    }


def _parse_all_links(soup: BeautifulSoup, source_url: str) -> List[Dict]:
    """Fallback: extract circulars from any links with number patterns."""
    circulars = []
    seen = set()

    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        if not text:
            continue

        circ_match = re.search(r'(\d+/\d+/\d{4}|\d+/\d{4})', text)
        if circ_match and re.search(r'circular|notification|order', text, re.IGNORECASE):
            circ_id = f"CBIC-{circ_match.group(1)}"
            if circ_id in seen:
                continue
            seen.add(circ_id)

            href = link["href"]
            if not href.startswith("http"):
                from urllib.parse import urlparse
                base = urlparse(source_url)
                href = f"{base.scheme}://{base.netloc}{href}" if href.startswith("/") else href

            circulars.append({
                "circular_id": circ_id,
                "title": text[:300],
                "text": text,
                "sections": list(set(re.findall(r'[Ss]ection\s+(\d+)', text))),
                "url": href,
                "issue_date": None,
            })

    return circulars


# ═══════════════════════════════════════════
# Manual entry — always works, no scraping needed
# ═══════════════════════════════════════════

async def add_manual_circular(db: AsyncSession, circular_id: str, title: str,
                               full_text: str, sections: List[str],
                               source_url: str = "") -> KBStaging:
    """Add a circular manually to staging (bypasses scraper)."""
    entry = KBStaging(
        circular_id=circular_id, title=title, full_text=full_text,
        sections=sections, source_url=source_url, status="UNVERIFIED",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info(f"Manual circular added: {circular_id}")
    return entry
