"use client";

import { useState, useEffect } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import Link from "next/link";
import { Edit3, CheckCircle2, AlertCircle } from "lucide-react";

interface Notice {
  id: string;
  case_id: string;
  notice_type: string;
  draft_status: string;
  demand_amount: number;
}

const API_BASE = "http://localhost:8000";

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/notices?page_size=100`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("taxshield_token") || ""}` },
    })
      .then((r) => r.json())
      .then((data) => {
        const items: Notice[] = Array.isArray(data) ? data : data.items || [];
        // Filter for items requiring draft review (not approved or finalized)
        const reviewable = items.filter(n => n.draft_status !== "approved" && n.draft_status !== "finalized");
        setDrafts(reviewable);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <AuthGuard><div className="page-container" style={{ textAlign: "center", paddingTop: "var(--space-16)", color: "var(--text-secondary)" }}>Loading drafts workspace...</div></AuthGuard>;

  return (
    <AuthGuard>
      <div className="page-container">
        <h1 className="page-title">Drafts Workspace</h1>
        <p className="page-subtitle">Review, modify, and approve AI-generated legal responses.</p>

        {drafts.length === 0 ? (
          <div className="empty-state" style={{ background: "white", borderRadius: "var(--radius-xl)", border: "1px solid var(--border-primary)", padding: "var(--space-16)" }}>
            <div style={{ display: "inline-flex", background: "var(--success-bg)", color: "var(--success)", padding: "var(--space-4)", borderRadius: "50%", marginBottom: "var(--space-4)" }}>
              <CheckCircle2 size={48} />
            </div>
            <h3 style={{ fontSize: "var(--font-lg)", fontWeight: 700, color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>Zero Backlog!</h3>
            <p style={{ color: "var(--text-secondary)" }}>All AI drafts have been reviewed and approved. No pending actions required.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "var(--space-5)" }}>
            {drafts.map(d => (
              <div key={d.id} className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-3)" }}>
                    <span className="badge-status status-review" style={{ background: "var(--warning-bg)", color: "var(--warning)" }}>Action Required</span>
                    <span style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>{d.notice_type || "General Notice"}</span>
                  </div>
                  <h3 style={{ fontSize: "var(--font-lg)", fontWeight: 700, color: "var(--text-primary)", marginBottom: "var(--space-1)" }}>{d.case_id}</h3>
                  <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
                    Draft generated. Awaiting human review before finalization. Demand: ₹{d.demand_amount?.toLocaleString() || "N/A"}.
                  </p>
                </div>
                <Link href={`/notice/${d.id}`} style={{ textDecoration: "none" }}>
                  <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }}>
                    <Edit3 size={16} /> Review Draft
                  </button>
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
