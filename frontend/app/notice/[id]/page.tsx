"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
import {
    ArrowLeft,
    Copy,
    Printer,
    CheckCircle2,
    Edit3,
    Loader2,
    FileText,
    Trash2,
    Save,
    X,
} from "lucide-react";
import { type NoticeDetail, fetchNotice, deleteNotice, updateDraft } from "@/lib/api";

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

    useEffect(() => {
        const load = async () => {
            try {
                const data = await fetchNotice(params.id as string);
                setNotice(data);
            } catch {
                setError("Could not load notice.");
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [params.id]);

    if (loading) {
        return (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100dvh", gap: "var(--space-3)", color: "var(--text-secondary)" }}>
                <Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} />
                Loading...
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    if (error || !notice) {
        return (
            <AuthGuard>
                <div style={{ padding: "var(--space-8)", textAlign: "center", color: "var(--text-secondary)" }}>
                    <p>{error || "Notice not found."}</p>
                    <button className="btn btn-ghost" onClick={() => router.push("/")} style={{ marginTop: "var(--space-4)" }}>
                        <ArrowLeft size={16} /> Back
                    </button>
                </div>
            </AuthGuard>
        );
    }

    const handleCopy = () => {
        if (notice.draft_reply) {
            navigator.clipboard.writeText(notice.draft_reply);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handlePrint = () => {
        if (!notice.draft_reply) return;
        const printWindow = window.open("", "_blank");
        if (!printWindow) return;

        const lines = notice.draft_reply.split("\n");
        let contentHtml = "";
        for (const line of lines) {
            if (/^[A-Z][A-Z\s\-—\/]+:?\s*$/.test(line)) {
                contentHtml += '<h3 style="margin-top:1.2em;margin-bottom:0.2em;font-size:15px">' + line + "</h3>";
            } else if (line.trim() === "" || line.trim() === "---") {
                contentHtml += '<div style="height:0.5em"></div>';
            } else if (/^\s*[\d]+\.\s/.test(line) || /^\s*[-•]\s/.test(line)) {
                contentHtml += '<div style="padding-left:1.5em;margin:0.2em 0">' + line + "</div>";
            } else {
                contentHtml += "<p>" + line + "</p>";
            }
        }

        const html = [
            "<!DOCTYPE html><html><head>",
            "<title>Draft Reply — " + notice.case_id + "</title>",
            "<style>",
            "@import url('https://fonts.googleapis.com/css2?family=Times+New+Roman:wght@400;700&display=swap');",
            "body{font-family:'Times New Roman', Times, serif;max-width:800px;margin:40px auto;padding:0 24px;color:#000;line-height:1.6;font-size:12pt}",
            "p{margin:0.5em 0}",
            "@media print{body{margin:0;padding:20mm}}",
            "</style></head><body>",
            '<div class="content">' + contentHtml + "</div>",
            "</body></html>",
        ].join("\n");

        printWindow.document.write(html);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => { printWindow.print(); }, 300);
    };

    const handleDelete = async () => {
        if (!window.confirm(`Delete notice "${notice.case_id}"? This cannot be undone.`)) return;
        setDeleting(true);
        try {
            await deleteNotice(notice.id);
            router.push("/");
        } catch {
            setDeleting(false);
            alert("Failed to delete.");
        }
    };

    const handleEditSave = async () => {
        setSaving(true);
        try {
            const result = await updateDraft(notice.id, editText);
            setNotice({ ...notice, draft_reply: result.draft_reply });
            setEditing(false);
        } catch {
            alert("Failed to save.");
        } finally {
            setSaving(false);
        }
    };

    // Render draft reply as clean formatted text
    const renderDraft = (text: string) => {
        return text.split("\n").map((line, idx) => {
            // Section headings (ALL CAPS lines)
            if (line.match(/^[A-Z][A-Z\s\-—\/]+:?\s*$/)) {
                return <div key={idx} style={{ fontWeight: 700, marginTop: "1.5em", marginBottom: "0.3em", fontSize: "0.95em", letterSpacing: "0.01em" }}>{line}</div>;
            }
            // Bold markdown **text**
            if (line.includes("**")) {
                const parts = line.split(/\*\*(.*?)\*\*/g);
                return (
                    <p key={idx} style={{ margin: "0.3em 0", lineHeight: 1.7 }}>
                        {parts.map((part, i) => i % 2 === 1 ? <strong key={i}>{part}</strong> : part)}
                    </p>
                );
            }
            // Table-like lines (contains | or tab-separated cols)
            if (line.includes("|") && line.trim().startsWith("|")) {
                return null; // handled separately
            }
            // Blank line → spacer
            if (line.trim() === "" || line.trim() === "---") {
                return <div key={idx} style={{ height: "0.6em" }} />;
            }
            // Numbered / bulleted list items
            if (line.match(/^\s*[\d]+\.\s/) || line.match(/^\s*[-•]\s/)) {
                return <div key={idx} style={{ paddingLeft: "1.5em", margin: "0.2em 0", lineHeight: 1.7 }}>{line}</div>;
            }
            return <p key={idx} style={{ margin: "0.3em 0", lineHeight: 1.7 }}>{line}</p>;
        });
    };

    return (
        <AuthGuard>
            <>
                {/* ── Toolbar ── */}
                <header style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    justifyContent: "space-between", 
                    paddingBottom: "var(--space-4)",
                    marginBottom: "var(--space-6)",
                    borderBottom: "1px solid var(--border-primary)" 
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
                        <button className="btn btn-outline btn-icon" onClick={() => router.push("/")} aria-label="Back" style={{ border: "none" }}>
                            <ArrowLeft size={20} />
                        </button>
                        <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                <FileText size={15} style={{ color: "var(--text-secondary)" }} />
                                <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                                    {notice.case_id}
                                </span>
                            </div>
                            <p style={{ margin: 0, fontSize: "var(--font-xs)", color: "var(--text-tertiary)", marginTop: 2 }}>
                                {notice.notice_type || "GST Notice"} {notice.fy ? `· FY ${notice.fy}` : ""} {notice.section ? `· Section ${notice.section}` : ""}
                            </p>
                        </div>
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                        {notice.draft_reply && !editing && (
                            <>
                                <button className="btn btn-outline" onClick={handleCopy} style={{ fontSize: "var(--font-sm)" }}>
                                    {copied ? <CheckCircle2 size={15} style={{ color: "var(--success)" }} /> : <Copy size={15} />} 
                                    {copied ? "Copied" : "Copy"}
                                </button>
                                <button className="btn btn-outline" onClick={handlePrint} style={{ fontSize: "var(--font-sm)" }}>
                                    <Printer size={15} /> Print
                                </button>
                                <button className="btn btn-outline" onClick={() => { setEditText(notice.draft_reply || ""); setEditing(true); }} style={{ fontSize: "var(--font-sm)" }}>
                                    <Edit3 size={15} /> Edit
                                </button>
                            </>
                        )}
                        {editing && (
                            <>
                                <button className="btn btn-ghost" onClick={() => setEditing(false)} disabled={saving}>
                                    <X size={15} /> Cancel
                                </button>
                                <button className="btn btn-primary" onClick={handleEditSave} disabled={saving}>
                                    <Save size={15} /> {saving ? "Saving..." : "Save"}
                                </button>
                            </>
                        )}
                        <button
                            className="btn btn-ghost btn-icon"
                            onClick={handleDelete}
                            disabled={deleting}
                            style={{ color: "var(--danger)" }}
                            title="Delete notice"
                            aria-label="Delete"
                        >
                            <Trash2 size={17} />
                        </button>
                    </div>
                </header>

                {/* ── Document Body ── */}
                <div style={{
                    maxWidth: 820,
                    margin: "0 auto",
                    padding: "var(--space-10) var(--space-6)",
                }}>
                    <style>{`
                        @media print {
                            header, .no-print { display: none !important; }
                            body { background: white !important; color: black !important; }
                            .doc-paper { box-shadow: none !important; border: none !important; background: white !important; color: black !important; }
                        }
                    `}</style>

                    {notice.status === "processing" ? (
                        <div style={{ textAlign: "center", padding: "var(--space-16)", color: "var(--text-secondary)" }}>
                            <Loader2 size={32} style={{ animation: "spin 1s linear infinite", marginBottom: "var(--space-4)" }} />
                            <div style={{ fontWeight: 600 }}>Processing your notice...</div>
                            <div style={{ fontSize: "var(--font-sm)", marginTop: "var(--space-2)" }}>This usually takes 20–60 seconds. Refresh when done.</div>
                        </div>
                    ) : notice.status === "error" ? (
                        <div style={{ textAlign: "center", padding: "var(--space-16)", color: "var(--danger)" }}>
                            <div style={{ fontWeight: 600 }}>Processing failed</div>
                            <div style={{ fontSize: "var(--font-sm)", marginTop: "var(--space-2)", color: "var(--text-secondary)" }}>{notice.error_message || "Unknown error"}</div>
                        </div>
                    ) : editing ? (
                        // ── Edit Mode ──
                        <div className="doc-paper" style={{
                            background: "var(--bg-secondary)",
                            border: "1px solid var(--border-primary)",
                            borderRadius: "var(--radius-lg)",
                            padding: "var(--space-6)",
                        }}>
                            <textarea
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                style={{
                                    width: "100%",
                                    minHeight: 600,
                                    padding: "var(--space-4)",
                                    fontFamily: "Georgia, 'Times New Roman', serif",
                                    fontSize: "0.925rem",
                                    lineHeight: 1.8,
                                    background: "var(--bg-primary)",
                                    color: "var(--text-primary)",
                                    border: "1px solid var(--brand-primary)",
                                    borderRadius: "var(--radius-md)",
                                    resize: "vertical",
                                    outline: "none",
                                }}
                            />
                        </div>
                    ) : notice.draft_reply ? (
                        // ── Document View ──
                        <div className="doc-paper" style={{
                            background: "var(--bg-secondary)",
                            border: "1px solid var(--border-primary)",
                            borderRadius: "var(--radius-lg)",
                            padding: "var(--space-10) var(--space-12)",
                            fontFamily: "Georgia, 'Times New Roman', serif",
                            fontSize: "0.925rem",
                            color: "var(--text-primary)",
                            lineHeight: 1.8,
                            boxShadow: "0 4px 24px rgba(0,0,0,0.15)",
                        }}>
                            {renderDraft(notice.draft_reply)}
                        </div>
                    ) : (
                        <div style={{ textAlign: "center", padding: "var(--space-16)", color: "var(--text-secondary)" }}>
                            <Edit3 size={32} style={{ marginBottom: "var(--space-4)" }} />
                            <div>No draft reply available yet.</div>
                        </div>
                    )}
                </div>
            </>
        </AuthGuard>
    );
}
