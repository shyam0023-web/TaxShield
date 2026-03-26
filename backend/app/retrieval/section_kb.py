"""
TaxShield — Section-Based Knowledge Base (Primary RAG Path)
WISC: Section-select lookup returns curated markdown in ~1ms.
FAISS hybrid search is the fallback for queries without a clear section match.

Usage:
    from app.retrieval.section_kb import section_kb
    results = section_kb.search_by_section("73")        # Primary: ~1ms
    results = section_kb.search_by_query("limitation")  # Fuzzy: ~1ms
"""
import os
import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated_kb")


@dataclass
class KBEntry:
    """A single curated KB entry loaded from markdown."""
    section: str                       # e.g. "73", "74", "din"
    filename: str                      # e.g. "section_73.md"
    title: str                         # First H1 heading
    full_text: str                     # Complete markdown content
    key_ruling: str                    # Text under ## Key Ruling
    defense_points: List[str]          # Bullet points under ## Key Defense Points
    keywords: List[str] = field(default_factory=list)  # Extracted from content


class SectionKB:
    """
    In-memory section-indexed knowledge base.
    Loaded once on startup from curated markdown files.
    """

    def __init__(self):
        self._entries: Dict[str, KBEntry] = {}   # section -> KBEntry
        self._all_entries: List[KBEntry] = []
        self._loaded = False

    def load(self, kb_dir: str = None):
        """Load all markdown files from curated_kb directory."""
        kb_dir = kb_dir or KB_DIR
        kb_dir = os.path.normpath(kb_dir)

        if not os.path.exists(kb_dir):
            # Try relative to backend/
            alt = os.path.join("backend", "data", "curated_kb")
            if os.path.exists(alt):
                kb_dir = alt
            else:
                logger.warning(f"Curated KB directory not found: {kb_dir}")
                self._loaded = True
                return

        count = 0
        for filename in sorted(os.listdir(kb_dir)):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(kb_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                entry = self._parse_markdown(filename, content)
                self._all_entries.append(entry)

                # Index by section number(s)
                # Primary section (from filename) always takes priority
                primary_secs, secondary_secs = self._extract_sections(filename, content)
                for sec in primary_secs:
                    self._entries[sec] = entry  # Always set primary
                for sec in secondary_secs:
                    if sec not in self._entries:  # Only set if no primary owner
                        self._entries[sec] = entry

                count += 1
            except Exception as e:
                logger.error(f"Failed to load KB file {filename}: {e}")

        self._loaded = True
        logger.info(f"Curated KB loaded: {count} files, {len(self._entries)} section mappings")

    def _parse_markdown(self, filename: str, content: str) -> KBEntry:
        """Parse a curated markdown file into a KBEntry."""
        # Extract title (first H1)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filename

        # Extract Key Ruling section
        key_ruling = self._extract_section_content(content, "Key Ruling")

        # Extract Defense Points as bullet list
        defense_text = self._extract_section_content(content, "Key Defense Points")
        defense_points = re.findall(r"^\d+\.\s+(.+)$", defense_text, re.MULTILINE)

        # Extract section from filename
        sec_match = re.search(r"section_(\d+)", filename)
        section = sec_match.group(1) if sec_match else filename.replace(".md", "")

        # Build keyword index from content
        keywords = self._extract_keywords(content)

        return KBEntry(
            section=section,
            filename=filename,
            title=title,
            full_text=content,
            key_ruling=key_ruling,
            defense_points=defense_points,
            keywords=keywords,
        )

    def _extract_section_content(self, content: str, heading: str) -> str:
        """Extract text under a ## heading until the next ## heading."""
        pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_sections(self, filename: str, content: str) -> tuple:
        """Extract section numbers this KB file covers.
        Returns (primary_sections, secondary_sections).
        Primary = from filename (owns the key). Secondary = from content references (fills gaps only)."""
        primary = []
        secondary = []

        # From filename: section_73.md → "73" (PRIMARY)
        sec_match = re.search(r"section_(\d+)", filename)
        if sec_match:
            primary.append(sec_match.group(1))

        # From content: references to "Section XX" (SECONDARY — don't override)
        for match in re.finditer(r"Section\s+(\d+)", content):
            sec = match.group(1)
            if sec not in primary and sec not in secondary:
                secondary.append(sec)

        # Special: DIN circular (PRIMARY)
        if "din" in filename.lower():
            primary.extend(["din", "128", "DIN"])

        return primary, secondary

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract meaningful keywords from content for fuzzy matching."""
        # Grab words from headings and bold text
        keywords = set()
        for match in re.finditer(r"\*\*(.+?)\*\*", content):
            keywords.add(match.group(1).lower())
        for match in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE):
            for word in match.group(1).lower().split():
                if len(word) > 3:
                    keywords.add(word)
        return list(keywords)

    # ═══════════════════════════════════════════
    # Search Methods
    # ═══════════════════════════════════════════

    def search_by_section(self, section: str) -> List[Dict]:
        """
        Primary path: O(1) dict lookup by section number.
        Returns curated KB entry for the given CGST section.
        Latency: ~0.1ms
        """
        if not self._loaded:
            self.load()

        # Try raw key first (for non-numeric like "din", "DIN")
        entry = self._entries.get(section)
        if not entry:
            # Normalize: "Section 73" → "73", "73(5)" → "73"
            sec_clean = re.sub(r"[^0-9]", "", str(section).split("(")[0])
            if sec_clean:
                entry = self._entries.get(sec_clean)
        if not entry:
            return []

        return [{
            "doc_id": f"KB-{entry.section}",
            "text": entry.key_ruling,
            "full_text": entry.full_text,
            "title": entry.title,
            "defense_points": entry.defense_points,
            "score": 1.0,
            "source": "curated_kb",
        }]

    def search_by_sections(self, sections: List[str]) -> List[Dict]:
        """
        Search for multiple sections at once.
        Returns deduplicated results ordered by section number.
        """
        seen = set()
        results = []
        for sec in sections:
            for result in self.search_by_section(sec):
                if result["doc_id"] not in seen:
                    seen.add(result["doc_id"])
                    results.append(result)
        return results

    def search_by_query(self, query: str) -> List[Dict]:
        """
        Fuzzy fallback: keyword match against all KB entries.
        Used when no direct section match is found.
        Latency: ~1ms (scans all entries)
        """
        if not self._loaded:
            self.load()

        query_lower = query.lower()
        query_words = set(re.findall(r"\w+", query_lower))
        scored = []

        for entry in self._all_entries:
            # Score based on keyword overlap
            keyword_overlap = len(query_words & set(entry.keywords))
            # Bonus for query terms appearing in key_ruling
            ruling_hits = sum(1 for w in query_words if w in entry.key_ruling.lower())
            # Bonus for title match
            title_hits = sum(1 for w in query_words if w in entry.title.lower())

            score = keyword_overlap * 0.3 + ruling_hits * 0.5 + title_hits * 0.2
            if score > 0:
                scored.append((entry, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return [{
            "doc_id": f"KB-{entry.section}",
            "text": entry.key_ruling,
            "full_text": entry.full_text,
            "title": entry.title,
            "defense_points": entry.defense_points,
            "score": round(score, 4),
            "source": "curated_kb",
        } for entry, score in scored[:5]]

    def search_din(self) -> List[Dict]:
        """Shortcut: get DIN circular KB entry."""
        return self.search_by_section("din")

    def get_all_sections(self) -> List[str]:
        """Return all indexed section numbers."""
        if not self._loaded:
            self.load()
        return sorted(self._entries.keys(), key=lambda x: (not x.isdigit(), x))

    def reload(self):
        """Hot-reload: clear indexes and re-read all markdown files from disk.
        Called after a new circular is approved and its markdown file is written."""
        logger.info("Reloading curated KB from disk...")
        self._entries.clear()
        self._all_entries.clear()
        self._loaded = False
        self.load()
        logger.info(f"KB reload complete: {len(self._all_entries)} entries, {len(self._entries)} sections")


# Singleton — lazy-loads on first search call
section_kb = SectionKB()
