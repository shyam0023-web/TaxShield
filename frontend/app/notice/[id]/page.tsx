"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft,
    FileText,
    Download,
    CheckCircle2,
    Edit3,
    XCircle,
    AlertTriangle,
    BookOpen,
    Copy,
    Printer,
    Loader2,
    Shield,
    Clock,
    TrendingUp,
} from "lucide-react";
import { type NoticeDetail, fetchNotice } from "@/lib/api";

function formatCurrency(amount: number): string {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
    }).format(amount);
}

export default function NoticeDetailPage() {
    const params = useParams();
    const router = useRouter();
    const [notice, setNotice] = useState<NoticeDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        const load = async () => {
            try {
                const data = await fetchNotice(params.id as string);
                setNotice(data);
            } catch {
                setError("Could not load notice. Make sure the backend is running at http://localhost:8000");
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [params.id]);

    // Loading state
    if (loading) {
        return (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100dvh", gap: "var(--space-3)", color: "var(--text-secondary)" }}>
                <Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} />
                Loading notice...
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    // Error / not found state
    if (error || !notice) {
        return (
            <>
                <header className="page-header">
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
                        <button className="btn btn-ghost btn-icon" onClick={() => router.push("/")} aria-label="Back to dashboard">
                            <ArrowLeft size={20} />
                        </button>
                        <h1 className="page-title" style={{ fontSize: "var(--font-lg)" }}>Notice Detail</h1>
                    </div>
                </header>
                <div className="empty-state">
                    <div className="empty-state-icon">
                        <FileText size={32} />
                    </div>
                    <div className="empty-state-title">
                        {error || "Notice not found"}
                    </div>
                    <div className="empty-state-text">
                        {error ? error : "The requested notice could not be loaded."}
                    </div>
                    <Link href="/" className="btn btn-primary">
                        <ArrowLeft size={16} />
                        Back to Dashboard
                    </Link>
                </div>
            </>
        );
    }

    // Extract display fields from entities
    const entities = notice.entities || {};
    const llmExtracted = typeof entities.llm_extracted === "string"
        ? (() => { try { return JSON.parse(entities.llm_extracted); } catch { return {}; } })()
        : (entities.llm_extracted || {});
    const gstins = (entities.GSTIN || []).map((g: any) => g.value || g).filter(Boolean);
    const primaryGstin = gstins[0] || "—";

    const riskClass =
        notice.risk_level === "HIGH"
            ? "badge-high"
            : notice.risk_level === "MEDIUM"
                ? "badge-medium"
                : "badge-low";

    const statusLabel = notice.status === "error" ? "Error"
        : notice.draft_status === "approved" ? "Approved"
        : notice.draft_status === "draft_ready" ? "Draft Ready"
        : notice.status === "processed" ? "Draft Ready"
        : "Processing";

    const statusClass = statusLabel === "Approved" ? "status-approved"
        : statusLabel === "Draft Ready" ? "status-draft-ready"
        : "status-processing";

    const handleCopy = () => {
        if (notice.draft_reply) {
            navigator.clipboard.writeText(notice.draft_reply);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <>
            {/* Page Header */}
            <header className="page-header">
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
                    <button
                        className="btn btn-ghost btn-icon"
                        onClick={() => router.push("/")}
                        aria-label="Back to dashboard"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                            <h1 className="page-title" style={{ fontSize: "var(--font-lg)" }}>
                                {notice.case_id}
                            </h1>
                            <span className={`badge ${riskClass}`}>
                                {notice.risk_level === "HIGH" && <AlertTriangle size={11} />}
                                {notice.risk_level}
                            </span>
                            {notice.is_time_barred && (
                                <span className="badge badge-low" style={{ gap: 4 }}>
                                    <Clock size={11} />
                                    Time-Barred
                                </span>
                            )}
                        </div>
                        <p className="page-subtitle">{notice.notice_type || notice.filename}</p>
                    </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span className={`status ${statusClass}`}>
                        <span className="status-dot" />
                        {statusLabel}
                    </span>
                </div>
            </header>

            {/* Split Screen Content */}
            <div className="split-container">
                {/* LEFT: Notice Details + Extracted Text */}
                <div className="split-left">
                    <div className="split-panel-header">
                        <span className="split-panel-title">
                            <FileText size={14} style={{ display: "inline", marginRight: 6 }} />
                            Notice Analysis
                        </span>
                    </div>

                    <div className="split-panel-body" style={{ padding: "var(--space-5)" }}>
                        {/* Key Info Grid */}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
                            <div style={{ padding: "var(--space-4)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>Section</div>
                                <div style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                                    {notice.section ? `Section ${notice.section}` : "—"}
                                </div>
                            </div>
                            <div style={{ padding: "var(--space-4)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>Demand</div>
                                <div style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                                    {notice.demand_amount > 0 ? formatCurrency(notice.demand_amount) : "—"}
                                </div>
                            </div>
                            <div style={{ padding: "var(--space-4)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>GSTIN</div>
                                <div style={{ fontSize: "var(--font-xs)", fontWeight: 500, color: "var(--text-primary)", fontFamily: "monospace" }}>
                                    {primaryGstin}
                                </div>
                            </div>
                            <div style={{ padding: "var(--space-4)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>Financial Year</div>
                                <div style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                                    {notice.fy || "—"}
                                </div>
                            </div>
                        </div>

                        {/* Risk Analysis */}
                        {notice.risk_reasoning && (
                            <div style={{ marginBottom: "var(--space-6)", padding: "var(--space-4)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                                    <Shield size={14} style={{ color: "var(--warning)" }} />
                                    <span style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                                        Risk Analysis ({notice.risk_level} — {Math.round((notice.risk_score || 0) * 100)}%)
                                    </span>
                                </div>
                                <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
                                    {notice.risk_reasoning}
                                </p>
                            </div>
                        )}

                        {/* Extracted Notice Text */}
                        <div>
                            <div style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--space-3)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                <BookOpen size={14} />
                                Extracted Notice Text
                            </div>
                            <div style={{
                                padding: "var(--space-4)",
                                background: "var(--bg-primary)",
                                borderRadius: "var(--radius-md)",
                                border: "1px solid var(--border-primary)",
                                maxHeight: 400,
                                overflowY: "auto",
                                fontSize: "var(--font-sm)",
                                color: "var(--text-secondary)",
                                lineHeight: 1.7,
                                whiteSpace: "pre-wrap",
                                fontFamily: "var(--font-mono, monospace)",
                            }}>
                                {notice.notice_text || "No text extracted."}
                            </div>
                        </div>
                    </div>
                </div>

                {/* RIGHT: AI Draft Reply */}
                <div className="split-right">
                    <div className="split-panel-header">
                        <span className="split-panel-title">
                            <Edit3 size={14} style={{ display: "inline", marginRight: 6 }} />
                            AI Draft Reply
                        </span>
                        {notice.draft_reply && (
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                                <button
                                    className="btn btn-ghost btn-icon"
                                    title={copied ? "Copied!" : "Copy"}
                                    aria-label="Copy draft"
                                    onClick={handleCopy}
                                >
                                    {copied ? <CheckCircle2 size={16} style={{ color: "var(--success)" }} /> : <Copy size={16} />}
                                </button>
                                <button className="btn btn-ghost btn-icon" title="Print" aria-label="Print draft" onClick={() => window.print()}>
                                    <Printer size={16} />
                                </button>
                            </div>
                        )}
                    </div>

                    <div className="split-panel-body">
                        {notice.draft_reply ? (
                            <div className="draft-reply animate-fade-in">
                                {notice.draft_reply.split("\n\n").map((paragraph, idx) => {
                                    // Section headings (lines in all caps or markdown bold)
                                    if (paragraph.startsWith("**") && paragraph.endsWith("**")) {
                                        return <h3 key={idx} style={{ marginTop: "var(--space-6)" }}>{paragraph.replace(/\*\*/g, "")}</h3>;
                                    }
                                    // Bold inline text
                                    if (paragraph.includes("**")) {
                                        const parts = paragraph.split(/\*\*(.*?)\*\*/g);
                                        return <p key={idx}>{parts.map((part, i) => i % 2 === 1 ? <strong key={i}>{part}</strong> : part)}</p>;
                                    }
                                    return <p key={idx}>{paragraph}</p>;
                                })}
                            </div>
                        ) : (
                            <div className="empty-state" style={{ padding: "var(--space-12) var(--space-8)" }}>
                                <div className="empty-state-icon">
                                    <Edit3 size={32} />
                                </div>
                                <div className="empty-state-title">No Draft Available</div>
                                <div className="empty-state-text">
                                    {notice.status === "error"
                                        ? `Processing failed: ${notice.error_message || "Unknown error"}`
                                        : "The AI draft reply will appear here once the notice has been processed."}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Action Bar */}
                    {notice.draft_reply && (
                        <div className="action-bar">
                            <div className="action-bar-left">
                                <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
                                    Generated {notice.updated_at ? new Date(notice.updated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : ""}
                                </span>
                            </div>
                            <div className="action-bar-right">
                                <button className="btn btn-danger" aria-label="Reject draft">
                                    <XCircle size={16} />
                                    Reject
                                </button>
                                <button className="btn btn-outline" aria-label="Edit draft">
                                    <Edit3 size={16} />
                                    Edit
                                </button>
                                <button className="btn btn-success" aria-label="Approve draft">
                                    <CheckCircle2 size={16} />
                                    Approve
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
