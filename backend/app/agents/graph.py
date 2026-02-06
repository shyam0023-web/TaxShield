from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.research import research
from app.agents.drafting import draft_reply
from app.agents.audit import audit
from app.watchdog.timebar import calculate_timebar, TimeBarRequest
from datetime import date

def check_timebar(state: AgentState) -> dict:
    request = TimeBarRequest(
        fy=state['fy'],
        section=state['section'],
        notice_date=date.today()
    )
    result = calculate_timebar(request)
    return {
        "is_time_barred": result.is_time_barred,
        "messages": [f"Time-bar check: {'BARRED' if result.is_time_barred else 'Valid'}"]
    }

def route_after_timebar(state: AgentState) -> str:
    if state.get('is_time_barred', False):
        return END
    return "research"

workflow = StateGraph(AgentState)

workflow.add_node("timebar", check_timebar)
workflow.add_node("research", research)
workflow.add_node("draft", draft_reply)
workflow.add_node("audit", audit)

workflow.set_entry_point("timebar")
workflow.add_conditional_edges("timebar", route_after_timebar, {END: END, "research": "research"})
workflow.add_edge("research", "draft")
workflow.add_edge("draft", "audit")
workflow.add_edge("audit", END)

app = workflow.compile()
