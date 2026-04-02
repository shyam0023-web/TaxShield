"use client";

import { useState, useEffect } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import Link from "next/link";
import {
  FileText,
  AlertTriangle,
  Search,
  CheckCircle2,
  Filter,
  ArrowRight,
  TrendingDown,
  Upload,
  Calendar,
  IndianRupee,
  ChevronRight,
  Lightbulb
} from "lucide-react";

interface Notice {
  id: string;
  case_id: string;
  filename: string;
  notice_type: string;
  fy: string;
  section: string;
  demand_amount: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
  draft_status: string;
  status: string;
  is_time_barred: boolean;
  response_deadline: string;
  created_at: string;
}

const API_BASE = "http://localhost:8000";

function formatCurrency(amount: number): string {
  if (amount === 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function DashboardPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    const fetchNotices = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/notices?page_size=100`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("taxshield_token") || ""}` },
        });
        if (res.ok) {
          const data = await res.json();
          const items: Notice[] = Array.isArray(data) ? data : (data.items || []);
          setNotices(items);

          const hasProcessing = items.some((n) => n.status === "processing");
          if (hasProcessing) {
            pollTimer = setTimeout(fetchNotices, 5000);
          }
        }
      } catch {
        console.error("Backend fetch error");
      } finally {
        setLoading(false);
      }
    };

    fetchNotices();
    return () => { if (pollTimer) clearTimeout(pollTimer); };
  }, []);

  const stats = {
    total: notices.length,
    highRisk: notices.filter((n) => n.risk_level === "HIGH").length,
    approved: notices.filter((n) => n.draft_status === "approved").length,
  };
  const approvalRate = stats.total > 0 ? Math.round((stats.approved / stats.total) * 100) : 0;

  const filteredNotices = notices.filter((n) => {
    return (
      searchQuery === "" ||
      n.case_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (n.notice_type && n.notice_type.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  });

  return (
    <AuthGuard>
      <div className="page-container">
        {/* Page Header */}
        <h1 className="page-title">Notice Ledger</h1>
        <p className="page-subtitle">
          Manage and respond to GST compliance inquiries with architectural precision.
        </p>

        {/* Top Stats Cards */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-card-header">
              <div className="stat-icon-wrapper" style={{ color: "var(--brand-secondary)" }}>
                <FileText size={18} strokeWidth={2.5} />
              </div>
              <span className="stat-badge" style={{ background: "#F3E8FF", color: "#9333EA" }}>TOTAL ACTIVE</span>
            </div>
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Cumulative Notices Received</div>
          </div>

          <div className="stat-card">
            <div className="stat-card-header">
              <div className="stat-icon-wrapper" style={{ color: "var(--danger)" }}>
                <AlertTriangle size={18} strokeWidth={2.5} />
              </div>
              <span className="stat-badge" style={{ background: "#FEE2E2", color: "#DC2626" }}>CRITICAL ACTION</span>
            </div>
            <div className="stat-value danger">{stats.highRisk.toString().padStart(2, '0')}</div>
            <div className="stat-label">High-Risk Liabilities Pending</div>
          </div>

          <div className="stat-card">
            <div className="stat-card-header">
              <div className="stat-icon-wrapper" style={{ color: "var(--text-secondary)" }}>
                <CheckCircle2 size={18} strokeWidth={2.5} />
              </div>
              <span className="stat-badge" style={{ background: "#F1F5F9", color: "#475569" }}>SYSTEM TRUST</span>
            </div>
            <div className="stat-value">{stats.total === 0 ? "—" : `${approvalRate}%`}</div>
            <div className="stat-label">Notice Approval Rate</div>
          </div>
        </div>

        {/* Data Table */}
        <div className="data-table-container">
          <div className="data-table-header">
            <div className="data-table-title">Recent GST Notices</div>
            <div style={{ display: "flex", gap: "var(--space-3)" }}>
              <div className="search-wrapper">
                <Search size={16} style={{ position: "absolute", left: 14, top: 12, color: "var(--text-tertiary)" }} />
                <input
                  type="text"
                  placeholder="Search notices..."
                  className="search-input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <button className="btn-icon"><Filter size={18} /></button>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>NOTICE TYPE</th>
                  <th>RISK LEVEL</th>
                  <th>DEMAND AMOUNT</th>
                  <th>DEADLINE</th>
                  <th>STATUS</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredNotices.length > 0 ? (
                  filteredNotices.map((notice) => (
                    <tr key={notice.id}>
                      <td>
                        {notice.notice_type || "Unknown Notice"}
                        <div className="td-subtitle">Ref: {notice.case_id}</div>
                      </td>
                      <td>
                        <span className={`badge-risk risk-${(notice.risk_level || "low").toLowerCase()}`}>
                          {notice.risk_level || "LOW"}
                        </span>
                      </td>
                      <td>{formatCurrency(notice.demand_amount)}</td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <Calendar size={14} color="var(--text-tertiary)"/>
                          {notice.created_at ? formatDate(notice.created_at) : "—"}
                        </div>
                      </td>
                      <td>
                        {notice.status === "processing" ? (
                          <span className="badge-status status-review">Processing</span>
                        ) : notice.draft_status === "approved" || notice.status === "processed" ? (
                          <span className="badge-status status-finalized">Finalized</span>
                        ) : (
                          <span className="badge-status status-drafting">Drafting</span>
                        )}
                      </td>
                      <td className="action-cell">
                        <Link href={`/notice/${notice.id}`}>
                          <button className="btn-icon" aria-label="View Notice">
                            <ChevronRight size={18} />
                          </button>
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "var(--space-8)" }}>
                      <div style={{ color: "var(--text-tertiary)", marginBottom: "var(--space-4)" }}>No notices found.</div>
                      <Link href="/upload" className="btn btn-primary" style={{ display: "inline-flex" }}>
                        <Upload size={16} /> Upload First Notice
                      </Link>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "var(--space-6)" }}>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
              Showing {filteredNotices.length} of {notices.length} notices
            </div>
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <button className="btn btn-outline" style={{ height: 36, padding: "0 16px" }} disabled>Previous</button>
              <button className="btn btn-primary" style={{ height: 36, padding: "0 16px" }} disabled>Next</button>
            </div>
          </div>
        </div>

        {/* Bottom Widgets */}
        <div className="widgets-grid">
          {/* Audit Timeline */}
          <div className="widget-card">
            <h3 className="widget-title">Audit Activity Timeline</h3>
            <div className="timeline">
              <div className="timeline-item">
                <div className="timeline-dot-wrapper">
                  <div className="timeline-dot" style={{ background: "var(--text-primary)" }}></div>
                  <div className="timeline-line"></div>
                </div>
                <div className="timeline-content">
                  <h4>Response Drafted</h4>
                  <p>Notice GSTIN-9841 • 2 hours ago</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-dot-wrapper">
                  <div className="timeline-dot" style={{ background: "var(--border-active)" }}></div>
                  <div className="timeline-line"></div>
                </div>
                <div className="timeline-content">
                  <h4 style={{ color: "var(--text-secondary)" }}>Document Uploaded</h4>
                  <p>ITC Verification Annexure • 5 hours ago</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-dot-wrapper">
                  <div className="timeline-dot" style={{ background: "var(--border-active)" }}></div>
                </div>
                <div className="timeline-content">
                  <h4 style={{ color: "var(--text-secondary)" }}>System Auto-Scan Complete</h4>
                  <p>12 new documents indexed • Yesterday</p>
                </div>
              </div>
            </div>
          </div>

          {/* Risk Insight */}
          <div className="widget-card insight-card">
            <div className="insight-content">
              <h3 className="widget-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                Risk Insight
              </h3>
              <p className="insight-text">
                Based on your GSTR-3B Mismatch trend, we recommend reconciling with 2A/2B data before the 20th of each month to avoid priority-high notices.
              </p>
              <button className="btn-light">Download Reconciliation Guide</button>
            </div>
            <Lightbulb size={160} color="var(--brand-primary)" opacity={0.03} style={{ position: "absolute", bottom: -30, right: -20, zIndex: 1 }} />
          </div>
        </div>

      </div>
    </AuthGuard>
  );
}
