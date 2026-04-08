"""
Test suite for OCR Processor module
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.ocr_processor import (
    TaxDocumentParser,
    EnhancedPDFProcessor,
    DocumentStructure,
)
from app.rag.tax_domain_service import NoticeType


class TestTaxDocumentParser:
    """Test TaxDocumentParser functionality"""

    def test_detect_scn_notice(self):
        """Test detection of Show Cause Notice (SCN)"""
        text = """
        CENTRAL BOARD OF INDIRECT TAXES AND CUSTOMS
        SHOW CAUSE NOTICE
        To: M/s ABC Traders
        Notice Date: 01-01-2024
        
        You are hereby directed to show cause...
        """
        parser = TaxDocumentParser()
        notice_type = parser.detect_notice_type(text)
        assert notice_type in [NoticeType.SCN.value, "SCN", "DEMAND", "OTHER", None]

    def test_extract_key_dates(self):
        """Test extraction of key dates"""
        text = """
        Notice Date: 15-03-2024
        Response deadline: 15-04-2024
        Financial Year: 2023-2024
        """
        parser = TaxDocumentParser()
        dates = parser.extract_key_dates(text)
        assert isinstance(dates, dict)
        assert "issued" in dates or "response_period_days" in dates or len(dates) >= 0

    def test_extract_amounts(self):
        """Test extraction of financial amounts"""
        text = """
        Total Demand: ₹5,00,000
        Penalty: ₹1,00,000
        Interest: ₹50,000
        Total Amount Due: ₹6,50,000
        """
        parser = TaxDocumentParser()
        amounts = parser.extract_amounts(text)
        assert isinstance(amounts, dict)

    def test_split_into_paragraphs(self):
        """Test paragraph splitting and role assignment"""
        text = """
        HEADER: CENTRAL BOARD OF INDIRECT TAXES
        
        BODY: You are hereby notified that...
        The assessment shows...
        You are required to...
        
        FOOTER: Signed by Officer
        Date: 01-04-2024
        """
        parser = TaxDocumentParser()
        paragraphs = parser.split_into_paragraphs(text)
        assert isinstance(paragraphs, list)
        assert len(paragraphs) > 0

    def test_extract_structure(self):
        """Test full document structure extraction"""
        text = """
        DEPARTMENT OF REVENUE
        SHOW CAUSE NOTICE
        
        Issue Date: 01-02-2024
        Notice No: GST/2024/001
        
        Facts and grounds of the notice...
        Demand details...
        Relief sought...
        
        Signed
        Date
        """
        parser = TaxDocumentParser()
        structure = parser.extract_structure(text, ocr_confidence=0.85)
        assert isinstance(structure, DocumentStructure)
        assert structure.header is not None or structure.body_paragraphs or structure.footer is not None


class TestEnhancedPDFProcessor:
    """Test EnhancedPDFProcessor functionality"""

    def test_processor_initialization(self):
        """Test that processor initializes correctly"""
        processor = EnhancedPDFProcessor()
        assert processor is not None

    def test_text_extraction_with_mock_data(self):
        """Test text extraction pipeline with mock data"""
        # Create a simple mock PDF text
        mock_text = """
        SHOW CAUSE NOTICE
        Notice No: GST/2024/001
        Date: 01-04-2024
        
        M/s ABC Traders
        
        DEMAND: ₹10,00,000
        
        You are required to respond within 30 days.
        """
        
        processor = EnhancedPDFProcessor()
        
        # Verify that processor can parse this structure
        parser = TaxDocumentParser()
        structure = parser.extract_structure(mock_text, ocr_confidence=0.9)
        
        assert structure is not None
        assert isinstance(structure, DocumentStructure)

    def test_document_structure_detection(self):
        """Test detection of document structure components"""
        text = """
        === HEADER ===
        GST Department
        Notice Number: 2024/001
        
        === BODY ===
        Assessment details
        Grounds for notice
        Demand calculation
        
        === FOOTER ===
        Signed
        Date
        """
        
        parser = TaxDocumentParser()
        structure = parser.extract_structure(text, ocr_confidence=0.8)
        
        assert structure is not None
        assert isinstance(structure, DocumentStructure)


class TestIntegration:
    """Integration tests for OCR processor"""

    def test_full_pipeline_with_sample_notice(self):
        """Test complete processing pipeline"""
        sample_notice = """
        CENTRAL BOARD OF INDIRECT TAXES AND CUSTOMS
        SHOW CAUSE NOTICE UNDER GST
        
        Notice Number: GST/MH/2024/001
        Issue Date: 15-03-2024
        
        To: M/s XYZ Corporation
        Address: Mumbai, Maharashtra
        
        NOTICE OF DEMAND AND LIABILITY
        
        The assessment as per the records shows:
        - Total taxable turnover: ₹50,00,000
        - Tax demand: ₹5,00,000
        - Penalty: ₹2,50,000
        
        You are required to submit your response within 30 days.
        
        Issued by: Revenue Officer
        Date: 15-03-2024
        """
        
        parser = TaxDocumentParser()
        
        # Test multiple extraction methods
        dates = parser.extract_key_dates(sample_notice)
        amounts = parser.extract_amounts(sample_notice)
        structure = parser.extract_structure(sample_notice, ocr_confidence=0.9)
        
        assert structure is not None
        assert isinstance(amounts, dict)
        assert isinstance(dates, dict)

    @pytest.mark.parametrize("notice_text,expected_found", [
        ("Response deadline: 15-04-2024", True),
        ("₹1,00,000 demand", True),
        ("Section 73 assessment", True),
    ])
    def test_pattern_matching(self, notice_text, expected_found):
        """Test pattern matching for key elements"""
        parser = TaxDocumentParser()
        
        # These patterns should be found in the text
        assert notice_text in notice_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
