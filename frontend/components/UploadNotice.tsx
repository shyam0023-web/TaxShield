"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadNotice, UploadResponse } from "@/lib/api";

export default function UploadNotice() {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<UploadResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        setError(null);
        try {
            const data = await uploadNotice(file);
            setResult(data);
        } catch (err: any) {
            setError(err.message || "Failed to analyze notice");
        } finally {
            setLoading(false);
        }
    };

    const riskColor = result?.risk_level === "HIGH" ? "#ef4444"
        : result?.risk_level === "MEDIUM" ? "#f59e0b"
        : "#22c55e";

    return (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-8)" }}>
            {/* Upload Card */}
            <div style={{
                padding: "var(--space-8)",
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-primary)",
                borderRadius: "var(--radius-lg)",
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
                    <div style={{
                        width: 48, height: 48, borderRadius: "var(--radius-lg)",
                        background: "linear-gradient(135deg, #6366f1, #a855f7)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                        <svg width="24" height="24" fill="none" stroke="white" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                    </div>
                    <div>
                        <h2 style={{ fontSize: "var(--font-lg)", fontWeight: 600, color: "var(--text-primary)" }}>Upload Notice</h2>
                        <p style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>PDF files up to 25MB</p>
                    </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                            GST Notice Document
                        </label>
                        <input
                            type="file"
                            accept=".pdf"
                            onChange={(e) => setFile(e.target.files?.[0] || null)}
                            style={{
                                width: "100%",
                                padding: "var(--space-4)",
                                background: "var(--bg-surface)",
                                border: "1px solid var(--border-primary)",
                                borderRadius: "var(--radius-md)",
                                color: "var(--text-primary)",
                                fontSize: "var(--font-sm)",
                                cursor: "pointer",
                            }}
                        />
                    </div>

                    <button
                        onClick={handleUpload}
                        disabled={!file || loading}
                        className="btn btn-primary"
                        style={{
                            width: "100%",
                            padding: "var(--space-4) var(--space-6)",
                            fontSize: "var(--font-base)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "var(--space-3)",
                            opacity: !file || loading ? 0.5 : 1,
                        }}
                    >
                        {loading ? (
                            <>
                                <svg style={{ animation: "spin 1s linear infinite" }} width="20" height="20" viewBox="0 0 24 24">
                                    <circle opacity="0.25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                    <path opacity="0.75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                Analyzing with AI...
                                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                            </>
                        ) : (
                            <>
                                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Analyze Notice
                            </>
                        )}
                    </button>

                    {error && (
                        <div style={{
                            padding: "var(--space-4)",
                            background: "var(--danger-bg)",
                            border: "1px solid var(--danger-border)",
                            borderRadius: "var(--radius-md)",
                            color: "var(--danger)",
                            fontSize: "var(--font-sm)",
                            display: "flex",
                            alignItems: "center",
                            gap: "var(--space-3)",
                        }}>
                            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {error}
                        </div>
                    )}
                </div>
            </div>

            {/* Result Card */}
            {result ? (
                <div style={{
                    padding: "var(--space-8)",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-active)",
                    borderRadius: "var(--radius-lg)",
                }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-6)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                            <div style={{
                                width: 48, height: 48, borderRadius: "var(--radius-lg)",
                                background: "linear-gradient(135deg, #22c55e, #14b8a6)",
                                display: "flex", alignItems: "center", justifyContent: "center",
                            }}>
                                <svg width="24" height="24" fill="none" stroke="white" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <div>
                                <h2 style={{ fontSize: "var(--font-lg)", fontWeight: 600, color: "var(--text-primary)" }}>Processing Complete</h2>
                                <p style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>Notice #{result.case_id}</p>
                            </div>
                        </div>
                        <span className={`badge badge-${result.risk_level?.toLowerCase() || "low"}`} style={{ color: riskColor }}>
                            {result.risk_level} Risk
                        </span>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
                            <div style={{ padding: "var(--space-4)", background: "var(--bg-surface)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", marginBottom: 4 }}>Status</div>
                                <div style={{ fontSize: "var(--font-base)", fontWeight: 600, color: "var(--text-primary)" }}>{result.status}</div>
                            </div>
                            <div style={{ padding: "var(--space-4)", background: "var(--bg-surface)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", marginBottom: 4 }}>Draft</div>
                                <div style={{ fontSize: "var(--font-base)", fontWeight: 600, color: "var(--text-primary)" }}>
                                    {result.draft_status === "draft_ready" ? "✅ Ready" : "⏳ Pending"}
                                </div>
                            </div>
                        </div>

                        <button
                            className="btn btn-primary"
                            style={{ width: "100%", padding: "var(--space-3) var(--space-6)" }}
                            onClick={() => router.push(`/notice/${result.id}`)}
                        >
                            View Full Analysis →
                        </button>
                    </div>
                </div>
            ) : (
                <div style={{
                    padding: "var(--space-8)",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-primary)",
                    borderRadius: "var(--radius-lg)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    textAlign: "center",
                    minHeight: 400,
                }}>
                    <div style={{
                        width: 80, height: 80, borderRadius: "50%",
                        background: "var(--info-bg)",
                        border: "1px solid var(--info-border)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        marginBottom: "var(--space-6)",
                    }}>
                        <svg width="40" height="40" fill="none" stroke="var(--info)" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <h3 style={{ fontSize: "var(--font-lg)", fontWeight: 600, color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>Ready to Analyze</h3>
                    <p style={{ color: "var(--text-tertiary)", maxWidth: 300 }}>
                        Upload a GST notice PDF to get an AI-powered legal response with relevant law citations
                    </p>
                </div>
            )}
        </div>
    );
}
