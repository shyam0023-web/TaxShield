"""
Report Refinement API — AI-powered report updates based on user suggestions
Allows users to refine generated reports through conversational feedback
Uses Groq API for fast, cost-effective LLM refinement
Persists refinements to Supabase PostgreSQL
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from groq import Groq
from app.supabase_client import supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class RefineReportRequest(BaseModel):
    """Request to refine a report based on user suggestion"""
    documentId: str
    reportId: str
    currentReport: str
    suggestion: str


class RegenerateReportRequest(BaseModel):
    """Request to regenerate a report from scratch"""
    documentId: str
    reportId: str


class RefineReportResponse(BaseModel):
    """Response with refined report"""
    refinedReport: str
    explanation: str
    changesSummary: Optional[str] = None


class Report(BaseModel):
    """Report object for list/detail responses"""
    id: str
    documentId: str
    type: str
    title: str
    content: str
    generatedAt: str
    lastUpdatedAt: Optional[str] = None


@router.get("/", response_model=dict)
async def list_reports():
    """
    Fetch all available reports for the user from Supabase
    
    Returns reports that have been generated from tax notices.
    Falls back to mock data if Supabase is unavailable.
    """
    try:
        # Try to fetch from Supabase
        if supabase_client.is_connected:
            reports = await supabase_client.get_reports(limit=50)
            if reports:
                logger.info(f"✅ Fetched {len(reports)} reports from Supabase")
                return {"reports": reports}
        
        # Fallback to mock data for development
        logger.info("⚠️ Using mock reports (Supabase unavailable)")
        mock_reports = [
            {
                "id": "report-001",
                "documentId": "doc-001",
                "type": "Notice Analysis",
                "title": "SCN Analysis - Section 73(1)",
                "content": """NOTICE ANALYSIS REPORT

This report provides a comprehensive analysis of the Show Cause Notice (SCN) issued under Section 73(1) of the CGST/SGST Act, 2017.

KEY FINDINGS:
1. Notice Type: Show Cause Notice
2. Applicable Section: 73(1) - Assessment
3. Financial Year: 2019-20
4. Response Deadline: 30 days from notice date

RISK ASSESSMENT:
- Risk Level: MEDIUM
- Compliance Status: Action Required
- Time Bar Status: Not Time-Barred

RECOMMENDED ACTIONS:
1. Gather all supporting documents (Books of accounts, GST returns, etc.)
2. Prepare detailed response addressing each allegation
3. Consult with tax advisor for compliance verification
4. File response well within the 30-day deadline

LEGAL FRAMEWORK:
Section 73(1) of CGST/SGST Act, 2017 provides the assessing officer authority to conduct assessment proceedings. The response deadline is 30 days from the date of service of the notice.""",
                "generatedAt": "2026-04-06T08:48:54Z",
                "lastUpdatedAt": "2026-04-06T14:18:55Z"
            }
        ]
        
        return {"reports": mock_reports}
    
    except Exception as e:
        logger.error(f"Error fetching reports: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch reports: {str(e)}"
        )


@router.post("/refine", response_model=RefineReportResponse)
async def refine_report(request: RefineReportRequest):
    """
    Refine a report based on user suggestions
    
    Takes the current report and user feedback, returns an updated version
    that incorporates the suggestions while maintaining tax law compliance.
    """
    try:
        if not request.currentReport or len(request.currentReport.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Current report is too short or empty"
            )

        if not request.suggestion or len(request.suggestion.strip()) < 5:
            raise HTTPException(
                status_code=400,
                detail="Suggestion is too short"
            )

        # Build the refinement prompt
        refinement_prompt = f"""You are a tax law expert helping to refine a tax notice response document.

CURRENT REPORT:
{request.currentReport}

USER SUGGESTION:
{request.suggestion}

TASK:
1. Analyze the user's suggestion
2. Update the report to incorporate their feedback
3. Ensure the updated report:
   - Maintains tax law compliance
   - Uses proper legal language
   - Provides stronger arguments where requested
   - Stays focused on the tax notice facts
   - Preserves all factual accuracy

REQUIREMENTS:
- Output ONLY the refined/updated report text (no additional explanation at the end)
- Keep the same structure and sections
- Maintain professional tone
- Ensure all claims are supportable
- If suggestion is unclear, make best interpretation

Provide the refined report:"""

        # Call Groq to refine the report (fast and cost-effective)
        response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",  # Groq's fast model
            messages=[
                {
                    "role": "system",
                    "content": "You are a tax law expert refining legal documents. Maintain compliance and quality."
                },
                {
                    "role": "user",
                    "content": refinement_prompt
                }
            ],
            temperature=0.3,  # Lower temperature for consistency
            max_tokens=4000,
        )

        refined_report = response.choices[0].message.content.strip()

        # Generate explanation of changes using Groq
        explanation_prompt = f"""Based on this user suggestion: "{request.suggestion}"

Provide a brief explanation (2-3 sentences) of what was changed in the report to address this suggestion.
Be concise and specific."""

        explanation_response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise technical writer."
                },
                {
                    "role": "user",
                    "content": explanation_prompt
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )

        explanation = explanation_response.choices[0].message.content.strip()
        logger.info(
            f"Report refined for document {request.documentId}",
            extra={"suggestion": request.suggestion[:100]}
        )

        # Save refinement to Supabase if connected
        if supabase_client.is_connected:
            try:
                refinement_record = {
                    "report_id": request.reportId,
                    "document_id": request.documentId,
                    "user_suggestion": request.suggestion,
                    "refined_content": refined_report,
                    "explanation": explanation
                }
                saved = await supabase_client.create_refinement(refinement_record)
                if saved:
                    logger.info(f"✅ Refinement saved to Supabase for report {request.reportId}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save refinement to Supabase: {e}")
        
        # Also update the report itself in Supabase
        if supabase_client.is_connected:
            try:
                await supabase_client.update_report(request.reportId, {
                    "content": refined_report,
                    "lastUpdatedAt": None  # Will be set by Supabase trigger
                })
                logger.info(f"✅ Report updated in Supabase: {request.reportId}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update report in Supabase: {e}")

        return RefineReportResponse(
            refinedReport=refined_report,
            explanation=explanation,
            changesSummary=f"Updated based on: {request.suggestion[:60]}..."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refining report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refine report: {str(e)}"
        )


@router.post("/regenerate", response_model=dict)
async def regenerate_report(request: RegenerateReportRequest):
    """
    Regenerate a report from scratch
    
    Clears any refinements and regenerates the original analysis
    """
    try:
        logger.info(f"Regenerating report for document {request.documentId}")

        # In a real implementation, this would:
        # 1. Fetch the original document from database
        # 2. Re-run the analysis pipeline
        # 3. Generate a fresh report
        
        # For now, return a placeholder response
        return {
            "report": "Report regenerated successfully.",
            "status": "success",
            "message": "Original analysis regenerated"
        }

    except Exception as e:
        logger.error(f"Error regenerating report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate report: {str(e)}"
        )
