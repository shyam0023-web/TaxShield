"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
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
    Trash2,
    ExternalLink,
    ChevronDown,
    ChevronUp,
} from "lucide-react";
import { type NoticeDetail, fetchNotice, deleteNotice, approveDraft, rejectDraft, updateDraft } from "@/lib/api";

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
    const [deleting, setDeleting] = useState(false);
    const [editing, setEditing] = useState(false);
    const [editText, setEditText] = useState("");
    const [saving, setSaving] = useState(false);
    const [showVerification, setShowVerification] = useState(false);

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

    const handleDelete = async () => {
        const confirmed = window.confirm(
            `Permanently delete notice "${notice.case_id}" and all associated data?\n\nThis action cannot be undone (DPDP Act — Right to Erasure).`
        );
        if (!confirmed) return;

        setDeleting(true);
        try {
            await deleteNotice(notice.id);
            router.push("/");
        } catch {
            setDeleting(false);
            alert("Failed to delete notice. Please try again.");
        }
    };

    const handleApprove = async () => {
        setSaving(true);
        try {
            await approveDraft(notice.id);
            setNotice({ ...notice, draft_status: "approved" });
        } catch {
            alert("Failed to approve draft.");
        } finally {
            setSaving(false);
        }
    };

    const handleReject = async () => {
        const feedback = window.prompt("Reason for rejection (optional):");
        setSaving(true);
        try {
            await rejectDraft(notice.id, feedback || undefined);
            setNotice({ ...notice, draft_status: "rejected" });
        } catch {
            alert("Failed to reject draft.");
        } finally {
            setSaving(false);
        }
    };

    const handleEditStart = () => {
        setEditText(notice.draft_reply || "");
        setEditing(true);
    };

    const handleEditSave = async () => {
        setSaving(true);
        try {
            const result = await updateDraft(notice.id, editText);
            setNotice({ ...notice, draft_reply: result.draft_reply, draft_status: "draft_ready" });
            setEditing(false);
        } catch {
            alert("Failed to save draft.");
        } finally {
            setSaving(false);
        }
    };

    return (
        <AuthGuard>
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
                    <button
                        className="btn btn-ghost"
                        onClick={handleDelete}
                        disabled={deleting}
                        style={{
                            color: "var(--danger)",
                            fontSize: "var(--font-sm)",
                            opacity: deleting ? 0.5 : 1,
                        }}
                        aria-label="Delete notice"
                    >
                        <Trash2 size={15} />
                        {deleting ? "Deleting..." : "Delete"}
                    </button>
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
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                            {notice.verification_status && (
                                <div
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 4,
                                        padding: "2px 10px",
                                        borderRadius: "var(--radius-full)",
                                        fontSize: "var(--font-xs)",
                                        fontWeight: 600,
                                        background: notice.verification_status === "passed"
                                            ? "rgba(34,197,94,0.15)"
                                            : notice.verification_status === "needs_review"
                                            ? "rgba(234,179,8,0.15)"
                                            : "rgba(239,68,68,0.15)",
                                        color: notice.verification_status === "passed"
                                            ? "#22c55e"
                                            : notice.verification_status === "needs_review"
                                            ? "#eab308"
                                            : "#ef4444",
                                        cursor: "pointer",
                                    }}
                                    onClick={() => setShowVerification(!showVerification)}
                                    title="Click to expand InEx verification details"
                                >
                                    {notice.verification_status === "passed" ? (
                                        <CheckCircle2 size={12} />
                                    ) : notice.verification_status === "needs_review" ? (
                                        <AlertTriangle size={12} />
                                    ) : (
                                        <XCircle size={12} />
                                    )}
                                    InEx {Math.round((notice.verification_score || 0) * 100)}%
                                    {showVerification ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                </div>
                            )}
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
                    </div>

                    {/* InEx Verification Details */}
                    {showVerification && notice.verification_issues && notice.verification_issues.length > 0 && (
                        <div style={{
                            padding: "var(--space-4)",
                            background: "var(--bg-tertiary)",
                            borderBottom: "1px solid var(--border-secondary)",
                            maxHeight: 250,
                            overflowY: "auto",
                        }}>
                            <div style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--space-3)" }}>
                                Verification Issues ({notice.verification_issues.length})
                            </div>
                            {notice.verification_issues.map((issue, idx) => (
                                <div key={idx} style={{
                                    padding: "var(--space-3)",
                                    marginBottom: "var(--space-2)",
                                    borderRadius: "var(--radius-md)",
                                    border: `1px solid ${
                                        issue.severity === "critical" ? "rgba(239,68,68,0.3)"
                                        : issue.severity === "warning" ? "rgba(234,179,8,0.3)"
                                        : "var(--border-secondary)"
                                    }`,
                                    background: issue.severity === "critical" ? "rgba(239,68,68,0.05)" : "var(--bg-primary)",
                                }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: 4 }}>
                                        <span style={{
                                            fontSize: 10,
                                            fontWeight: 700,
                                            textTransform: "uppercase",
                                            color: issue.severity === "critical" ? "#ef4444" : issue.severity === "warning" ? "#eab308" : "var(--text-tertiary)",
                                        }}>
                                            {issue.severity}
                                        </span>
                                        <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>
                                            {issue.stage.replace("_", " ")}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: "var(--font-sm)", color: "var(--text-primary)", marginBottom: 4 }}>
                                        {issue.issue}
                                    </div>
                                    {issue.suggestion && (
                                        <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", fontStyle: "italic" }}>
                                            💡 {issue.suggestion}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="split-panel-body">
                        {editing ? (
                            <div style={{ padding: "var(--space-4)" }}>
                                <textarea
                                    value={editText}
                                    onChange={(e) => setEditText(e.target.value)}
                                    style={{
                                        width: "100%",
                                        minHeight: 400,
                                        padding: "var(--space-4)",
                                        fontFamily: "var(--font-mono, monospace)",
                                        fontSize: "var(--font-sm)",
                                        lineHeight: 1.7,
                                        background: "var(--bg-primary)",
                                        color: "var(--text-primary)",
                                        border: "1px solid var(--brand-primary)",
                                        borderRadius: "var(--radius-md)",
                                        resize: "vertical",
                                        outline: "none",
                                    }}
                                />
                                <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "flex-end", marginTop: "var(--space-3)" }}>
                                    <button className="btn btn-ghost" onClick={() => setEditing(false)} disabled={saving}>
                                        Cancel
                                    </button>
                                    <button className="btn btn-primary" onClick={handleEditSave} disabled={saving}>
                                        {saving ? "Saving..." : "Save Changes"}
                                    </button>
                                </div>
                            </div>
                        ) : notice.draft_reply ? (
                            <div className="draft-reply animate-fade-in">
                                {notice.draft_reply.split("\n\n").map((paragraph, idx) => {
                                    if (paragraph.startsWith("**") && paragraph.endsWith("**")) {
                                        return <h3 key={idx} style={{ marginTop: "var(--space-6)" }}>{paragraph.replace(/\*\*/g, "")}</h3>;
                                    }
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
                    {notice.draft_reply && !editing && (
                        <div className="action-bar">
                            <div className="action-bar-left">
                                <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
                                    {notice.draft_status === "approved" ? "✅ Approved" : notice.draft_status === "rejected" ? "❌ Rejected" : `Generated ${notice.updated_at ? new Date(notice.updated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : ""}`}
                                </span>
                            </div>
                            <div className="action-bar-right">
                                {notice.draft_status !== "approved" && (
                                    <>
                                        <button className="btn btn-danger" aria-label="Reject draft" onClick={handleReject} disabled={saving}>
                                            <XCircle size={16} />
                                            {saving ? "..." : "Reject"}
                                        </button>
                                        <button className="btn btn-outline" aria-label="Edit draft" onClick={handleEditStart} disabled={saving}>
                                            <Edit3 size={16} />
                                            Edit
                                        </button>
                                        <button className="btn btn-success" aria-label="Approve draft" onClick={handleApprove} disabled={saving}>
                                            <CheckCircle2 size={16} />
                                            {saving ? "..." : "Approve"}
                                        </button>
                                    </>
                                )}
                                {notice.draft_status === "approved" && (
                                    <button className="btn btn-outline" aria-label="Edit draft" onClick={handleEditStart}>
                                        <Edit3 size={16} />
                                        Revise
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
        </AuthGuard>
    );
}
