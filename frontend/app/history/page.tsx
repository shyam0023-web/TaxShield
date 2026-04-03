"use client";

import { useState, useEffect } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import Link from "next/link";
import { Calendar, ChevronRight, FileText, Search, Clock, ShieldCheck } from "lucide-react";

interface Notice {
  id: string;
  case_id: string;
  filename: string;
  notice_type: string;
  fy: string;
  section: string;
  demand_amount: number;
  risk_level: string;
  status: string;
  draft_status: string;
  created_at: string;
}

import { API_BASE } from "@/lib/config";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}

export default function HistoryPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/notices?page_size=100`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("taxshield_token") || ""}` },
        });
        if (res.ok) {
          const data = await res.json();
          const items: Notice[] = Array.isArray(data) ? data : (data.items || []);
          // Sort chronologically (newest first)
          items.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
          setNotices(items);
        }
      } catch (err) {
        console.error("Failed to fetch history");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <AuthGuard>
      <div className="page-container">
        <h1 className="page-title">Upload History</h1>
        <p className="page-subtitle">A chronological log of all notices uploaded and processed by TaxShield.</p>

        <div className="data-table-container">
          <div className="data-table-header">
            <div className="data-table-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Clock style={{ color: "var(--brand-primary)" }} size={20} />
              Chronological Upload Log
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>DATE & TIME</th>
                  <th>FILE / CASE ID</th>
                  <th>AI PROCESSING DOC TYPE</th>
                  <th>SYSTEM STATUS</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} style={{ textAlign:"center", padding: "var(--space-6)" }}>Loading history...</td></tr>
                ) : notices.length > 0 ? (
                  notices.map((notice) => (
                    <tr key={notice.id}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 500 }}>
                          <Calendar size={14} color="var(--text-tertiary)" />
                          {notice.created_at ? formatDate(notice.created_at) : "Unknown Date"}
                        </div>
                      </td>
                      <td>
                        <div style={{ color: "var(--text-primary)", fontWeight: 600 }}>{notice.filename}</div>
                        <div className="td-subtitle">Ref: {notice.case_id}</div>
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <FileText size={14} color="var(--text-tertiary)" />
                          {notice.notice_type || "Document pending extraction"}
                        </div>
                      </td>
                      <td>
                        {notice.status === "processing" ? (
                           <span className="badge-status status-review" style={{ background: "var(--warning-bg)", color: "var(--warning)" }}>
                             Processing AI Analysis
                           </span>
                        ) : (
                           <span className="badge-status status-finalized" style={{ background: "var(--success-bg)", color: "var(--success)" }}>
                             <ShieldCheck size={14} /> Completed
                           </span>
                        )}
                      </td>
                      <td className="action-cell">
                        <Link href={`/notice/${notice.id}`}>
                          <button className="btn-light" style={{ padding: "6px 12px", border: "1px solid var(--border-primary)"}}>
                            View Details
                          </button>
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "var(--space-8)" }}>
                      <div style={{ color: "var(--text-tertiary)" }}>No upload history found.</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
