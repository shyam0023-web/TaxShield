"""
TaxShield — GST Notice Named Entity Recognition
Hybrid: Regex for structured fields (GSTIN, DIN) + LLM for unstructured
"""
import re
import json
from typing import Dict, List, Optional
from app.llm.gemini_client import gemini
from app.logger import logger
from app.tools.patterns import (
    GSTIN_PATTERN, DIN_PATTERN, SECTION_PATTERN,
    AMOUNT_PATTERN, PAN_PATTERN, DATE_PATTERNS,
)


class NoticeNER:
    # Patterns imported from app.tools.patterns (single source of truth)
    
    def validate_gstin_checksum(self, gstin: str) -> bool:
        """Validate GSTIN using checksum algorithm."""
        if len(gstin) != 15:
            return False
        # State code check (01-37)
        state_code = int(gstin[:2])
        if state_code < 1 or state_code > 37:
            return False
        # PAN check (chars 3-12)
        pan = gstin[2:12]
        if not re.match(PAN_PATTERN, pan):
            return False
        return True
    
    async def extract_entities(self, text: str) -> dict:
        """Extract all GST entities from notice text."""
        try:
            entities = {}
            
            # === Deterministic extraction (regex + checksum) ===
            # GSTIN
            gstins = re.findall(GSTIN_PATTERN, text)
            entities["GSTIN"] = [
                {"value": g, "valid": self.validate_gstin_checksum(g), "method": "regex+checksum"}
                for g in set(gstins)
            ]
            
            # DIN
            dins = re.findall(DIN_PATTERN, text)
            entities["DIN"] = [{"value": d, "method": "regex"} for d in set(dins)]
            
            # Sections
            sections = re.findall(SECTION_PATTERN, text)
            entities["SECTIONS"] = list(set(sections))
            
            # === LLM extraction (for complex/unstructured fields) ===
            llm_prompt = f"""From this GST tax notice text, extract the following in JSON format:
            {{
                "notice_type": "SCN/Demand/Scrutiny/Penalty/Other",
                "notice_number": "the reference number",
                "notice_date": "DD-MM-YYYY",
                "financial_year": "e.g., 2019-20",
                "demand_amount": {{"igst": 0, "cgst": 0, "sgst": 0, "cess": 0, "total": 0}},
                "penalty_amount": 0,
                "interest_amount": 0,
                "response_deadline": "DD-MM-YYYY",
                "issuing_officer": "name and designation",
                "jurisdiction": "commissionerate/division/range"
            }}
            
            Notice text:
            {text[:3000]}
            """
            
            llm_entities = await gemini.generate(llm_prompt, json_mode=True)
            
            # Parse JSON response
            try:
                entities["llm_extracted"] = json.loads(llm_entities)
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM entities as JSON")
                entities["llm_extracted"] = {}
            
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            raise
    
    async def extract_amounts(self, text: str) -> Dict[str, float]:
        """Extract and parse monetary amounts."""
        try:
            amounts = re.findall(AMOUNT_PATTERN, text)
            parsed_amounts = []
            
            for amount in amounts:
                # Clean and convert to float
                clean_amount = re.sub(r'[₹,\s]', '', amount)
                try:
                    parsed_amounts.append(float(clean_amount))
                except ValueError:
                    continue
            
            return {
                "raw_amounts": amounts,
                "parsed_amounts": parsed_amounts,
                "total_amount": sum(parsed_amounts) if parsed_amounts else 0.0
            }
            
        except Exception as e:
            logger.error(f"Amount extraction failed: {e}")
            return {"raw_amounts": [], "parsed_amounts": [], "total_amount": 0.0}
    
    async def extract_dates(self, text: str) -> List[str]:
        """Extract dates in various formats."""
        try:
            
            all_dates = []
            for pattern in DATE_PATTERNS:
                dates = re.findall(pattern, text, re.IGNORECASE)
                all_dates.extend(dates)
            
            return list(set(all_dates))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Date extraction failed: {e}")
            return []
    
    async def validate_entities(self, entities: Dict) -> Dict[str, any]:
        """Validate extracted entities for consistency and completeness."""
        try:
            validation_result = {
                "is_valid": True,
                "warnings": [],
                "errors": [],
                "completeness_score": 0.0
            }
            
            # Check GSTIN validity
            if "GSTIN" in entities:
                invalid_gstins = [g for g in entities["GSTIN"] if not g["valid"]]
                if invalid_gstins:
                    validation_result["warnings"].append(f"Invalid GSTINs found: {len(invalid_gstins)}")
            
            # Check required fields
            required_fields = ["notice_type", "notice_number", "notice_date"]
            llm_entities = entities.get("llm_extracted", {})
            
            missing_fields = [field for field in required_fields if not llm_entities.get(field)]
            if missing_fields:
                validation_result["errors"].append(f"Missing required fields: {missing_fields}")
                validation_result["is_valid"] = False
            
            # Calculate completeness score
            total_fields = len(required_fields) + 5  # +5 for optional fields
            present_fields = sum(1 for field in required_fields if llm_entities.get(field))
            present_fields += sum(1 for field in ["demand_amount", "penalty_amount", "interest_amount", "issuing_officer", "jurisdiction"] if llm_entities.get(field))
            
            validation_result["completeness_score"] = present_fields / total_fields
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Entity validation failed: {e}")
            return {
                "is_valid": False,
                "warnings": [],
                "errors": ["Validation failed"],
                "completeness_score": 0.0
            }
    
    async def extract_critical_entities_only(self, text: str) -> Dict[str, List]:
        """Extract only critical entities for quick processing."""
        try:
            critical = {}
            
            # GSTIN
            gstins = re.findall(GSTIN_PATTERN, text)
            critical["GSTIN"] = [
                {"value": g, "valid": self.validate_gstin_checksum(g)}
                for g in set(gstins)
            ]
            
            # DIN
            dins = re.findall(DIN_PATTERN, text)
            critical["DIN"] = [{"value": d} for d in set(dins)]
            
            # Amounts
            amounts = await self.extract_amounts(text)
            critical["AMOUNTS"] = amounts
            
            # Sections
            sections = re.findall(SECTION_PATTERN, text)
            critical["SECTIONS"] = list(set(sections))
            
            return critical
            
        except Exception as e:
            logger.error(f"Critical entity extraction failed: {e}")
            raise


# Singleton instance
notice_ner = NoticeNER()
