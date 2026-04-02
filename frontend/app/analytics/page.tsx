"use client";

import { useState, useEffect } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import {
  BarChart3, AlertTriangle, TrendingUp, ShieldAlert,
  FileText, Scale, IndianRupee, Activity
} from "lucide-react";

const API_BASE = "http://localhost:8000";

interface Analytics {
  total_notices: number;
  risk_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  draft_distribution: Record<string, number>;
  approval_rate: number;
  time_barred_count: number;
  avg_verification_score: number | null;
  avg_demand_amount: number | null;
  type_distribution: Record<string, number>;
  total_audit_events: number;
}

function DistributionBar({ data, colors }: { data: Record<string, number>; colors: Record<string, string> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return <p style={{ color: "var(--text-tertiary)", fontSize: "var(--font-sm)" }}>No data yet.</p>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {Object.entries(data).map(([key, count]) => {
        const pct = total ? Math.round((count / total) * 100) : 0;
        const color = colors[key] ?? "var(--border-active)";
        return (
          <div key={key}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)", textTransform: "capitalize" }}>{key.toLowerCase()}</span>
              <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{count} · {pct}%</span>
            </div>
            <div style={{ height: 8, background: "var(--bg-primary)", borderRadius: "var(--radius-full)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: "var(--radius-full)", transition: "width 0.6s ease" }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/analytics`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("taxshield_token") || ""}` },
    })
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <AuthGuard>
        <div className="page-container" style={{ textAlign: "center", paddingTop: "var(--space-16)", color: "var(--text-secondary)" }}>
          Loading analytics...
        </div>
      </AuthGuard>
    );
  }

  const riskColors: Record<string, string> = {
    HIGH: "var(--danger)", MEDIUM: "var(--risk-med-text)", LOW: "var(--brand-secondary)", UNKNOWN: "var(--text-tertiary)"
  };
  const typeColors: Record<string, string> = {
    SCN: "#6366f1", ASMT: "#f59e0b", DRC: "#ec4899", Unknown: "#94a3b8"
  };

  return (
    <AuthGuard>
      <div className="page-container">
        <h1 className="page-title">Analytics</h1>
        <p className="page-subtitle">Deep dive into your GST notice portfolio with AI-powered metrics.</p>

        {/* Top KPI cards */}
        <div className="stats-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: "var(--space-8)" }}>
          {[
            {
              label: "Total Notices", value: data?.total_notices ?? 0,
              icon: <FileText size={18} />, badge: "PORTFOLIO", badgeClr: "#F3E8FF", badgeText: "#9333EA"
            },
            {
              label: "Time-Barred", value: data?.time_barred_count ?? 0,
              icon: <ShieldAlert size={18} />, badge: "CRITICAL", badgeClr: "#FEE2E2", badgeText: "#DC2626"
            },
            {
              label: "AI Trust Score", value: data?.avg_verification_score != null ? `${data.avg_verification_score}` : "—",
              icon: <Activity size={18} />, badge: "AVG SCORE", badgeClr: "#DBEAFE", badgeText: "#2563EB"
            },
            {
              label: "Approval Rate", value: data?.approval_rate != null ? `${data.approval_rate}%` : "—",
              icon: <TrendingUp size={18} />, badge: "SYSTEM TRUST", badgeClr: "#F1F5F9", badgeText: "#475569"
            },
          ].map((s) => (
            <div className="stat-card" key={s.label}>
              <div className="stat-card-header">
                <div className="stat-icon-wrapper">{s.icon}</div>
                <span className="stat-badge" style={{ background: s.badgeClr, color: s.badgeText }}>{s.badge}</span>
              </div>
              <div className="stat-value">{String(s.value)}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Distribution Charts */}
        <div className="widgets-grid">
          <div className="widget-card">
            <h3 className="widget-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <AlertTriangle size={16} /> Risk Distribution
            </h3>
            <DistributionBar data={data?.risk_distribution ?? {}} colors={riskColors} />
          </div>

          <div className="widget-card">
            <h3 className="widget-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <FileText size={16} /> Notice Type Breakdown
            </h3>
            <DistributionBar data={data?.type_distribution ?? {}} colors={typeColors} />
          </div>

          <div className="widget-card">
            <h3 className="widget-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <BarChart3 size={16} /> Draft Status Breakdown
            </h3>
            <DistributionBar
              data={data?.draft_distribution ?? {}}
              colors={{ approved: "var(--success)", rejected: "var(--danger)", pending: "var(--warning)", review: "var(--risk-med-text)" }}
            />
          </div>

          <div className="widget-card">
            <h3 className="widget-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <IndianRupee size={16} /> Average Demand Exposure
            </h3>
            {data?.avg_demand_amount != null ? (
              <div>
                <div className="stat-value" style={{ fontSize: "var(--font-2xl)", marginBottom: "var(--space-2)" }}>
                  ₹{Number(data.avg_demand_amount).toLocaleString("en-IN")}
                </div>
                <div className="stat-label">Average demand across all notices</div>
              </div>
            ) : (
              <p style={{ color: "var(--text-tertiary)", fontSize: "var(--font-sm)" }}>No demand data available yet.</p>
            )}
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
