"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft,
    FileText,
    Download,
    ZoomIn,
    ZoomOut,
    CheckCircle2,
    Edit3,
    XCircle,
    AlertTriangle,
    BookOpen,
    Copy,
    ExternalLink,
    Printer,
    Loader2,
} from "lucide-react";

interface NoticeDetail {
    id: string;
    notice_number: string;
    date: string;
    section: string;
    demand_amount: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    status: "Processing" | "Draft Ready" | "Approved";
    taxpayer_name: string;
    issuing_authority: string;
    gstin: string;
    financial_year: string;
    due_date: string;
    pdf_url?: string;
    draft_reply?: DraftReply;
}

interface DraftReply {
    subject: string;
    body: string;
    citations: Citation[];
    generated_at: string;
    confidence_score: number;
}

interface Citation {
    id: string;
    section: string;
    text: string;
    source: string;
}

const API_BASE = "http://localhost:8000";

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
    const [activeCitation, setActiveCitation] = useState<string | null>(null);

    useEffect(() => {
        const fetchNotice = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/notices/${params.id}`);
                if (res.ok) {
                    const data = await res.json();
                    setNotice(data);
                } else {
                    setError("Notice not found.");
                }
            } catch {
                setError("Could not connect to backend. Make sure the server is running at " + API_BASE);
            } finally {
                setLoading(false);
            }
        };
        fetchNotice();
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

    const riskClass =
        notice.risk_level === "HIGH"
            ? "badge-high"
            : notice.risk_level === "MEDIUM"
                ? "badge-medium"
                : "badge-low";

    const draft = notice.draft_reply;

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
                                {notice.notice_number}
                            </h1>
                            <span className={`badge ${riskClass}`}>
                                {notice.risk_level === "HIGH" && <AlertTriangle size={11} />}
                                {notice.risk_level}
                            </span>
                        </div>
                        <p className="page-subtitle">{notice.taxpayer_name}</p>
                    </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span
                        className={`status ${notice.status === "Processing"
                                ? "status-processing"
                                : notice.status === "Draft Ready"
                                    ? "status-draft-ready"
                                    : "status-approved"
                            }`}
                    >
                        <span className="status-dot" />
                        {notice.status}
                    </span>
                </div>
            </header>

            {/* Split Screen Content */}
            <div className="split-container">
                {/* LEFT: PDF Viewer */}
                <div className="split-left">
                    <div className="split-panel-header">
                        <span className="split-panel-title">
                            <FileText size={14} style={{ display: "inline", marginRight: 6 }} />
                            Original Notice
                        </span>
                        <div style={{ display: "flex", gap: "var(--space-2)" }}>
                            <button className="btn btn-ghost btn-icon" title="Zoom In" aria-label="Zoom in">
                                <ZoomIn size={16} />
                            </button>
                            <button className="btn btn-ghost btn-icon" title="Zoom Out" aria-label="Zoom out">
                                <ZoomOut size={16} />
                            </button>
                            <button className="btn btn-ghost btn-icon" title="Download" aria-label="Download PDF">
                                <Download size={16} />
                            </button>
                        </div>
                    </div>

                    <div className="pdf-viewer">
                        {notice.pdf_url ? (
                            <iframe
                                src={notice.pdf_url}
                                style={{ width: "100%", height: "100%", border: "none" }}
                                title="Notice PDF"
                            />
                        ) : (
                            <div className="pdf-placeholder animate-fade-in">
                                <FileText size={48} strokeWidth={1} />
                                <div style={{ fontSize: "var(--font-lg)", fontWeight: 600, color: "var(--text-secondary)" }}>
                                    PDF Viewer
                                </div>
                                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)", textAlign: "center", maxWidth: 300, lineHeight: 1.6 }}>
                                    The original notice PDF will appear here when available.
                                </div>

                                {/* Notice metadata summary */}
                                <div style={{ width: "100%", maxWidth: 400, marginTop: "var(--space-6)", padding: "var(--space-4)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)", fontSize: "var(--font-sm)" }}>
                                        <div>
                                            <div style={{ color: "var(--text-tertiary)", fontSize: "var(--font-xs)" }}>Section</div>
                                            <div style={{ color: "var(--text-primary)", fontWeight: 500 }}>{notice.section}</div>
                                        </div>
                                        <div>
                                            <div style={{ color: "var(--text-tertiary)", fontSize: "var(--font-xs)" }}>Demand</div>
                                            <div style={{ color: "var(--text-primary)", fontWeight: 600 }}>{formatCurrency(notice.demand_amount)}</div>
                                        </div>
                                        <div>
                                            <div style={{ color: "var(--text-tertiary)", fontSize: "var(--font-xs)" }}>GSTIN</div>
                                            <div style={{ color: "var(--text-primary)", fontWeight: 500, fontFamily: "monospace", fontSize: "var(--font-xs)" }}>{notice.gstin}</div>
                                        </div>
                                        <div>
                                            <div style={{ color: "var(--text-tertiary)", fontSize: "var(--font-xs)" }}>Due Date</div>
                                            <div style={{ color: "var(--danger)", fontWeight: 600 }}>
                                                {new Date(notice.due_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* RIGHT: AI Draft Reply */}
                <div className="split-right">
                    <div className="split-panel-header">
                        <span className="split-panel-title">
                            <Edit3 size={14} style={{ display: "inline", marginRight: 6 }} />
                            AI Draft Reply
                        </span>
                        {draft && (
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                                <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                                    <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: draft.confidence_score >= 0.8 ? "var(--success)" : draft.confidence_score >= 0.6 ? "var(--warning)" : "var(--danger)" }} />
                                    Confidence: {Math.round(draft.confidence_score * 100)}%
                                </span>
                                <button className="btn btn-ghost btn-icon" title="Copy" aria-label="Copy draft" onClick={() => navigator.clipboard.writeText(draft.body)}>
                                    <Copy size={16} />
                                </button>
                                <button className="btn btn-ghost btn-icon" title="Print" aria-label="Print draft" onClick={() => window.print()}>
                                    <Printer size={16} />
                                </button>
                            </div>
                        )}
                    </div>

                    <div className="split-panel-body">
                        {draft ? (
                            <div className="draft-reply animate-fade-in">
                                {/* Subject */}
                                <div style={{ background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", padding: "var(--space-4)", marginBottom: "var(--space-6)", border: "1px solid var(--border-secondary)" }}>
                                    <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--space-1)" }}>Subject</div>
                                    <div style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)" }}>{draft.subject}</div>
                                </div>

                                {/* Body */}
                                {draft.body.split("\n\n").map((paragraph, idx) => {
                                    if (paragraph.startsWith("**") && paragraph.endsWith("**")) {
                                        return <h3 key={idx} style={{ marginTop: "var(--space-6)" }}>{paragraph.replace(/\*\*/g, "")}</h3>;
                                    }
                                    if (paragraph.includes("**")) {
                                        const parts = paragraph.split(/\*\*(.*?)\*\*/g);
                                        return <p key={idx}>{parts.map((part, i) => i % 2 === 1 ? <strong key={i}>{part}</strong> : part)}</p>;
                                    }
                                    return <p key={idx}>{paragraph}</p>;
                                })}

                                {/* Citations */}
                                {draft.citations && draft.citations.length > 0 && (
                                    <div style={{ marginTop: "var(--space-8)", borderTop: "1px solid var(--border-primary)", paddingTop: "var(--space-6)" }}>
                                        <h3 style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-4)" }}>
                                            <BookOpen size={14} />
                                            Citations ({draft.citations.length})
                                        </h3>
                                        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                                            {draft.citations.map((citation) => (
                                                <div key={citation.id} style={{ padding: "var(--space-4)", background: activeCitation === citation.id ? "var(--info-bg)" : "var(--bg-tertiary)", border: `1px solid ${activeCitation === citation.id ? "var(--info-border)" : "var(--border-secondary)"}`, borderRadius: "var(--radius-md)", cursor: "pointer", transition: "all var(--transition-fast)" }} onClick={() => setActiveCitation(activeCitation === citation.id ? null : citation.id)}>
                                                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                                                        <span className="citation">{citation.section}</span>
                                                        <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>{citation.source}</span>
                                                    </div>
                                                    <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginTop: "var(--space-2)", lineHeight: 1.5 }}>{citation.text}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="empty-state" style={{ padding: "var(--space-12) var(--space-8)" }}>
                                <div className="empty-state-icon">
                                    <Edit3 size={32} />
                                </div>
                                <div className="empty-state-title">No Draft Available</div>
                                <div className="empty-state-text">
                                    The AI draft reply will appear here once the notice has been processed.
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Action Bar */}
                    {draft && (
                        <div className="action-bar">
                            <div className="action-bar-left">
                                <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
                                    Generated {new Date(draft.generated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
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
