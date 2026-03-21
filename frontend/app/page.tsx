"use client";

import { useState, useEffect } from "react";
import { AuthGuard } from "@/components/AuthGuard";

import Link from "next/link";
import { NotificationPanel } from "@/components/NotificationPanel";
import {
  FileText,
  Calendar,
  IndianRupee,
  AlertTriangle,
  Upload,
  Search,
  Filter,
  Clock,
  CheckCircle2,
  FileCheck,
  TrendingUp,
  ArrowRight,
  Loader2,
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

function RiskBadge({ level }: { level: "LOW" | "MEDIUM" | "HIGH" }) {
  const className = `badge badge-${level.toLowerCase()}`;
  const icon =
    level === "HIGH" ? (
      <AlertTriangle size={11} />
    ) : level === "MEDIUM" ? (
      <TrendingUp size={11} />
    ) : (
      <CheckCircle2 size={11} />
    );

  return (
    <span className={className}>
      {icon}
      {level}
    </span>
  );
}

function StatusIndicator({
  status,
  draftStatus,
}: {
  status: string;
  draftStatus?: string;
}) {
  let label = "Processing";
  let statusClass = "status-processing";

  if (status === "error") {
    label = "Error";
    statusClass = "status-processing";
  } else if (draftStatus === "approved") {
    label = "Approved";
    statusClass = "status-approved";
  } else if (draftStatus === "draft_ready") {
    label = "Draft Ready";
    statusClass = "status-draft-ready";
  } else if (status === "processed") {
    label = "Draft Ready";
    statusClass = "status-draft-ready";
  }

  return (
    <span className={`status ${statusClass}`}>
      <span className="status-dot" />
      {label}
    </span>
  );
}

function StatCard({
  icon: Icon,
  value,
  label,
  color,
}: {
  icon: React.ElementType;
  value: string | number;
  label: string;
  color: string;
}) {
  return (
    <div className="stat-card stagger-item">
      <div
        className="stat-card-icon"
        style={{
          background: `${color}18`,
          color: color,
        }}
      >
        <Icon size={20} />
      </div>
      <div className="stat-card-value">{value}</div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}

function NoticeCard({ notice }: { notice: Notice }) {
  const displayRisk = notice.risk_level === "UNKNOWN" ? "LOW" : notice.risk_level;
  return (
    <Link
      href={`/notice/${notice.id}`}
      style={{ textDecoration: "none", color: "inherit" }}
    >
      <div className="notice-card stagger-item">
        <div className="notice-card-header">
          <RiskBadge level={displayRisk as "LOW" | "MEDIUM" | "HIGH"} />
          <StatusIndicator status={notice.status} draftStatus={notice.draft_status} />
        </div>

        <div className="notice-card-body">
          <div className="notice-card-number">{notice.case_id}</div>
          {notice.notice_type && notice.notice_type !== "Unknown" && (
            <div
              style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}
            >
              {notice.notice_type}
            </div>
          )}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "var(--space-3)",
          }}
        >
          <div className="notice-card-meta">
            <Calendar />
            {notice.created_at ? formatDate(notice.created_at) : "—"}
          </div>
          <div className="notice-card-meta">
            <FileText />
            {notice.section ? `Section ${notice.section}` : notice.fy || "—"}
          </div>
        </div>

        <div className="notice-card-footer">
          <div className="notice-card-amount">
            {notice.demand_amount > 0 ? (
              <>
                <span
                  style={{
                    fontSize: "var(--font-xs)",
                    color: "var(--text-tertiary)",
                    fontWeight: 400,
                  }}
                >
                  Demand
                </span>
                <br />
                {formatCurrency(notice.demand_amount)}
              </>
            ) : (
              <span style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>
                No Demand
              </span>
            )}
          </div>
          <div
            className="btn btn-ghost"
            style={{ fontSize: "var(--font-xs)", gap: "var(--space-1)" }}
          >
            View Details <ArrowRight size={14} />
          </div>
        </div>
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterRisk, setFilterRisk] = useState<string>("ALL");

  useEffect(() => {
    const fetchNotices = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/notices?page_size=100`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("taxshield_token") || ""}` },
        });
        if (res.ok) {
          const data = await res.json();
          setNotices(Array.isArray(data) ? data : (data.items || []));
        }
      } catch {
        // Backend not running — show empty state
      } finally {
        setLoading(false);
      }
    };
    fetchNotices();
  }, []);

  const stats = {
    total: notices.length,
    processing: notices.filter((n) => n.status === "processing").length,
    draftReady: notices.filter((n) => n.draft_status === "draft_ready" || n.status === "processed").length,
    approved: notices.filter((n) => n.draft_status === "approved").length,
  };

  const filteredNotices = notices.filter((n) => {
    const matchesSearch =
      searchQuery === "" ||
      n.case_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (n.notice_type &&
        n.notice_type.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesFilter = filterRisk === "ALL" || n.risk_level === filterRisk;

    return matchesSearch && matchesFilter;
  });

  return (
    <AuthGuard>
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            Manage and track GST notice responses
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
          <NotificationPanel />
          <Link href="/upload" className="btn btn-primary">
            <Upload size={16} />
            Upload Notice
          </Link>
        </div>
      </header>

      <div style={{ padding: "var(--space-8)" }}>
        {/* Stats */}
        <div className="stats-grid" style={{ marginBottom: "var(--space-8)" }}>
          <StatCard
            icon={FileText}
            value={stats.total}
            label="Total Notices"
            color="#3b82f6"
          />
          <StatCard
            icon={Clock}
            value={stats.processing}
            label="Processing"
            color="#f59e0b"
          />
          <StatCard
            icon={FileCheck}
            value={stats.draftReady}
            label="Draft Ready"
            color="#6366f1"
          />
          <StatCard
            icon={CheckCircle2}
            value={stats.approved}
            label="Approved"
            color="#22c55e"
          />
        </div>

        {/* Search & Filter Bar */}
        <div
          style={{
            display: "flex",
            gap: "var(--space-3)",
            marginBottom: "var(--space-6)",
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              flex: 1,
              minWidth: 280,
              position: "relative",
            }}
          >
            <Search
              size={16}
              style={{
                position: "absolute",
                left: "var(--space-4)",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-tertiary)",
              }}
            />
            <input
              type="text"
              placeholder="Search by notice number or taxpayer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "var(--space-3) var(--space-4) var(--space-3) 42px",
                background: "var(--bg-surface)",
                border: "1px solid var(--border-primary)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                fontSize: "var(--font-sm)",
                outline: "none",
                minHeight: 44,
                transition: "all var(--transition-fast)",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "var(--border-active)";
                e.target.style.boxShadow = "var(--shadow-glow)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "var(--border-primary)";
                e.target.style.boxShadow = "none";
              }}
            />
          </div>

          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            {["ALL", "LOW", "MEDIUM", "HIGH"].map((level) => (
              <button
                key={level}
                className={`btn ${filterRisk === level ? "btn-primary" : "btn-outline"}`}
                onClick={() => setFilterRisk(level)}
                style={{ fontSize: "var(--font-xs)", padding: "var(--space-2) var(--space-4)" }}
              >
                {level === "ALL" ? (
                  <>
                    <Filter size={14} />
                    All
                  </>
                ) : (
                  level
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Notices Grid */}
        {filteredNotices.length > 0 ? (
          <div className="notices-grid">
            {filteredNotices.map((notice) => (
              <NoticeCard key={notice.id} notice={notice} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">
              <FileText size={32} />
            </div>
            <div className="empty-state-title">No Notices Found</div>
            <div className="empty-state-text">
              {searchQuery || filterRisk !== "ALL"
                ? "Try adjusting your search or filter criteria."
                : "Upload your first GST notice to get started."}
            </div>
            <Link href="/upload" className="btn btn-primary">
              <Upload size={16} />
              Upload Notice
            </Link>
          </div>
        )}
      </div>
    </>
    </AuthGuard>
  );
}
