"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
import { getAuthHeaders } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import {
    Upload,
    FileText,
    X,
    CheckCircle2,
    AlertCircle,
    CloudUpload,
    File,
    ArrowLeft,
    Shield,
    Lock,
    Eye,
    Trash2,
} from "lucide-react";

type UploadStatus = "idle" | "dragging" | "uploading" | "success" | "error";

export default function UploadPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<UploadStatus>("idle");
    const [progress, setProgress] = useState(0);
    const [showConsent, setShowConsent] = useState(false);
    const [consentChecked, setConsentChecked] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setStatus("dragging");
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setStatus("idle");
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setStatus("idle");

        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && (droppedFile.type === "application/pdf" || droppedFile.name.toLowerCase().endsWith(".pdf"))) {
            setFile(droppedFile);
            setErrorMessage("");
        } else {
            setFile(null);
            setErrorMessage("Please upload a PDF file.");
        }
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile && (selectedFile.type === "application/pdf" || selectedFile.name.toLowerCase().endsWith(".pdf"))) {
            setFile(selectedFile);
            setErrorMessage("");
        } else {
            setFile(null);
            setErrorMessage("Please upload a PDF file.");
        }
    };

    const removeFile = () => {
        setFile(null);
        setStatus("idle");
        setProgress(0);
        setErrorMessage("");
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / 1048576).toFixed(1) + " MB";
    };

    const handleUploadClick = () => {
        if (!file) return;
        // Check if user already consented in this session
        const hasConsented = localStorage.getItem("taxshield_consent") === "true";
        if (hasConsented) {
            handleUpload();
        } else {
            setShowConsent(true);
            setConsentChecked(false);
        }
    };

    const handleConsentAccept = () => {
        localStorage.setItem("taxshield_consent", "true");
        setShowConsent(false);
        handleUpload();
    };

    const handleUpload = async () => {
        if (!file) return;

        setStatus("uploading");
        setProgress(0);
        setErrorMessage("");

        const formData = new FormData();
        formData.append("file", file);

        try {
            // Show progress while uploading
            const progressInterval = setInterval(() => {
                setProgress((prev) => {
                    if (prev >= 90) {
                        clearInterval(progressInterval);
                        return prev;
                    }
                    return prev + Math.random() * 15;
                });
            }, 300);

            const res = await fetch(`${API_BASE}/api/notices/upload`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: formData,
            });

            clearInterval(progressInterval);

            if (res.ok) {
                setProgress(100);
                setStatus("success");
                setTimeout(() => {
                    router.push("/");
                }, 2000);
            } else {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Upload failed (${res.status})`);
            }
        } catch (err: unknown) {
            setStatus("error");
            setProgress(0);
            const message = err instanceof Error ? err.message : "Upload failed";
            setErrorMessage(message.includes("fetch") 
                ? "Upload failed. Make sure the backend server is running."
                : message
            );
        }
    };

    return (
        <AuthGuard>
        <>
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
                        <h1 className="page-title">Upload Notice</h1>
                        <p className="page-subtitle">Upload a GST notice PDF for AI-powered analysis</p>
                    </div>
                </div>
            </header>

            <div
                style={{
                    padding: "var(--space-8)",
                    maxWidth: 720,
                    margin: "0 auto",
                }}
            >
                {/* Upload Zone */}
                {status !== "success" && (
                    <div
                        className={`upload-zone ${status === "dragging" ? "drag-over" : ""} animate-fade-in`}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                        role="button"
                        tabIndex={0}
                        aria-label="Drop PDF file here or click to browse"
                        onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                                fileInputRef.current?.click();
                            }
                        }}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".pdf"
                            onChange={handleFileSelect}
                            style={{ display: "none" }}
                            aria-hidden="true"
                        />

                        <div className="upload-zone-icon">
                            <CloudUpload size={28} />
                        </div>

                        <div className="upload-zone-title">
                            {status === "dragging"
                                ? "Drop your file here"
                                : "Drag & drop your PDF notice"}
                        </div>
                        <div className="upload-zone-subtitle">
                            or click to browse from your computer
                        </div>
                        <div
                            style={{
                                marginTop: "var(--space-4)",
                                fontSize: "var(--font-xs)",
                                color: "var(--text-tertiary)",
                            }}
                        >
                            Supports PDF files up to 25 MB
                        </div>
                    </div>
                )}

                {/* Error Message */}
                {errorMessage && (
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "var(--space-2)",
                            padding: "var(--space-3) var(--space-4)",
                            background: "var(--danger-bg)",
                            border: "1px solid var(--danger-border)",
                            borderRadius: "var(--radius-md)",
                            marginTop: "var(--space-4)",
                            fontSize: "var(--font-sm)",
                            color: "var(--danger)",
                        }}
                    >
                        <AlertCircle size={16} />
                        {errorMessage}
                    </div>
                )}

                {/* Selected File Card */}
                {file && status !== "success" && (
                    <div className="file-card animate-scale-in">
                        <div className="file-card-icon">
                            <FileText size={24} />
                        </div>
                        <div className="file-card-info">
                            <div className="file-card-name">{file.name}</div>
                            <div className="file-card-size">{formatFileSize(file.size)}</div>
                        </div>
                        {status !== "uploading" && (
                            <button
                                className="btn btn-ghost btn-icon"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    removeFile();
                                }}
                                aria-label="Remove file"
                            >
                                <X size={18} />
                            </button>
                        )}
                    </div>
                )}

                {/* Progress Bar */}
                {status === "uploading" && (
                    <div className="progress-container animate-fade-in">
                        <div className="progress-bar-bg">
                            <div
                                className="progress-bar-fill"
                                style={{ width: `${Math.min(progress, 100)}%` }}
                            />
                        </div>
                        <div className="progress-text">
                            <span>Uploading & Analyzing...</span>
                            <span style={{ fontVariantNumeric: "tabular-nums" }}>
                                {Math.round(Math.min(progress, 100))}%
                            </span>
                        </div>

                        {/* Processing Steps */}
                        <div
                            style={{
                                marginTop: "var(--space-6)",
                                display: "flex",
                                flexDirection: "column",
                                gap: "var(--space-3)",
                            }}
                        >
                            {[
                                { label: "Uploading document", threshold: 20 },
                                { label: "Running OCR extraction", threshold: 40 },
                                { label: "Identifying notice type & sections", threshold: 60 },
                                { label: "Generating AI draft reply", threshold: 80 },
                                { label: "Cross-referencing citations", threshold: 95 },
                            ].map((step, idx) => (
                                <div
                                    key={idx}
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "var(--space-3)",
                                        fontSize: "var(--font-sm)",
                                        color:
                                            progress >= step.threshold
                                                ? "var(--success)"
                                                : progress >= step.threshold - 20
                                                    ? "var(--text-primary)"
                                                    : "var(--text-tertiary)",
                                        transition: "color var(--transition-normal)",
                                    }}
                                >
                                    {progress >= step.threshold ? (
                                        <CheckCircle2 size={16} />
                                    ) : (
                                        <div
                                            style={{
                                                width: 16,
                                                height: 16,
                                                borderRadius: "50%",
                                                border: `2px solid ${progress >= step.threshold - 20
                                                    ? "var(--brand-primary)"
                                                    : "var(--border-primary)"
                                                    }`,
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "center",
                                            }}
                                        >
                                            {progress >= step.threshold - 20 && (
                                                <div
                                                    style={{
                                                        width: 6,
                                                        height: 6,
                                                        borderRadius: "50%",
                                                        background: "var(--brand-primary)",
                                                        animation: "pulse-dot 1s ease-in-out infinite",
                                                    }}
                                                />
                                            )}
                                        </div>
                                    )}
                                    {step.label}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Success State */}
                {status === "success" && (
                    <div className="empty-state animate-scale-in">
                        <div
                            className="empty-state-icon"
                            style={{
                                background: "var(--success-bg)",
                                border: "1px solid var(--success-border)",
                                color: "var(--success)",
                            }}
                        >
                            <CheckCircle2 size={40} />
                        </div>
                        <div className="empty-state-title">Upload Successful!</div>
                        <div className="empty-state-text">
                            Your notice has been uploaded and analyzed. The AI draft reply is
                            being generated. Redirecting to dashboard...
                        </div>
                        <div
                            style={{
                                width: 40,
                                height: 4,
                                borderRadius: "var(--radius-full)",
                                background: "var(--bg-tertiary)",
                                margin: "var(--space-4) auto 0",
                                overflow: "hidden",
                            }}
                        >
                            <div
                                style={{
                                    height: "100%",
                                    background: "var(--success)",
                                    borderRadius: "var(--radius-full)",
                                    animation: "shimmer 1.5s infinite linear",
                                    width: "100%",
                                }}
                            />
                        </div>
                    </div>
                )}

                {/* Upload Button */}
                {file && status === "idle" && (
                    <div
                        style={{
                            marginTop: "var(--space-6)",
                            display: "flex",
                            justifyContent: "center",
                        }}
                    >
                        <button
                            className="btn btn-primary animate-fade-in"
                            onClick={handleUploadClick}
                            style={{
                                padding: "var(--space-4) var(--space-8)",
                                fontSize: "var(--font-base)",
                            }}
                        >
                            <Upload size={18} />
                            Upload & Analyze
                        </button>
                    </div>
                )}

                {/* Help Text */}
                {status === "idle" && !file && (
                    <div
                        style={{
                            marginTop: "var(--space-8)",
                            textAlign: "center",
                        }}
                    >
                        <div
                            style={{
                                display: "inline-flex",
                                flexDirection: "column",
                                gap: "var(--space-3)",
                                fontSize: "var(--font-sm)",
                                color: "var(--text-tertiary)",
                                lineHeight: 1.6,
                            }}
                        >
                            <div
                                style={{
                                    fontWeight: 600,
                                    color: "var(--text-secondary)",
                                    marginBottom: "var(--space-1)",
                                }}
                            >
                                How it works
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                <span
                                    style={{
                                        width: 24,
                                        height: 24,
                                        borderRadius: "var(--radius-full)",
                                        background: "var(--info-bg)",
                                        border: "1px solid var(--info-border)",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        fontSize: "var(--font-xs)",
                                        fontWeight: 700,
                                        color: "var(--info)",
                                        flexShrink: 0,
                                    }}
                                >
                                    1
                                </span>
                                Upload your GST notice as a PDF
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                <span
                                    style={{
                                        width: 24,
                                        height: 24,
                                        borderRadius: "var(--radius-full)",
                                        background: "var(--info-bg)",
                                        border: "1px solid var(--info-border)",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        fontSize: "var(--font-xs)",
                                        fontWeight: 700,
                                        color: "var(--info)",
                                        flexShrink: 0,
                                    }}
                                >
                                    2
                                </span>
                                AI extracts notice details via OCR
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                <span
                                    style={{
                                        width: 24,
                                        height: 24,
                                        borderRadius: "var(--radius-full)",
                                        background: "var(--info-bg)",
                                        border: "1px solid var(--info-border)",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        fontSize: "var(--font-xs)",
                                        fontWeight: 700,
                                        color: "var(--info)",
                                        flexShrink: 0,
                                    }}
                                >
                                    3
                                </span>
                                Draft reply generated with legal citations
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* ═══ DPDP Consent Modal ═══ */}
            {showConsent && (
                <div
                    style={{
                        position: "fixed",
                        inset: 0,
                        zIndex: 1000,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        padding: "var(--space-4)",
                    }}
                >
                    {/* Backdrop */}
                    <div
                        style={{
                            position: "absolute",
                            inset: 0,
                            background: "rgba(0, 0, 0, 0.6)",
                            backdropFilter: "blur(4px)",
                        }}
                        onClick={() => setShowConsent(false)}
                    />

                    {/* Modal */}
                    <div
                        className="animate-scale-in"
                        style={{
                            position: "relative",
                            background: "var(--bg-primary)",
                            borderRadius: "var(--radius-xl)",
                            border: "1px solid var(--border-primary)",
                            maxWidth: 520,
                            width: "100%",
                            padding: "var(--space-8)",
                            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                        }}
                    >
                        {/* Header */}
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
                            <div
                                style={{
                                    width: 44,
                                    height: 44,
                                    borderRadius: "var(--radius-lg)",
                                    background: "var(--info-bg)",
                                    border: "1px solid var(--info-border)",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    color: "var(--info)",
                                    flexShrink: 0,
                                }}
                            >
                                <Shield size={22} />
                            </div>
                            <div>
                                <div style={{ fontWeight: 700, fontSize: "var(--font-lg)", color: "var(--text-primary)" }}>
                                    Data Processing Consent
                                </div>
                                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>
                                    DPDP Act, 2023 Compliance
                                </div>
                            </div>
                            <button
                                className="btn btn-ghost btn-icon"
                                onClick={() => setShowConsent(false)}
                                style={{ marginLeft: "auto" }}
                                aria-label="Close"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Content */}
                        <div
                            style={{
                                fontSize: "var(--font-sm)",
                                color: "var(--text-secondary)",
                                lineHeight: 1.7,
                                marginBottom: "var(--space-6)",
                            }}
                        >
                            <p style={{ marginBottom: "var(--space-4)" }}>
                                By uploading this notice, you consent to the following:
                            </p>

                            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                                {[
                                    { icon: Eye, text: "Your notice will be processed by AI to extract text, identify sections, and generate a draft reply." },
                                    { icon: Lock, text: "Personal identifiers (PAN, Aadhaar, phone) are redacted before AI processing. Business identifiers (GSTIN) are preserved." },
                                    { icon: Shield, text: "OCR runs locally on our servers — your document images never leave our infrastructure." },
                                    { icon: Trash2, text: "You can request deletion of your data at any time under the DPDP Act." },
                                ].map((item, i) => (
                                    <div key={i} style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-start" }}>
                                        <item.icon size={16} style={{ flexShrink: 0, marginTop: 3, color: "var(--brand-primary)" }} />
                                        <span>{item.text}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Consent Checkbox */}
                        <label
                            style={{
                                display: "flex",
                                alignItems: "flex-start",
                                gap: "var(--space-3)",
                                padding: "var(--space-4)",
                                background: "var(--bg-secondary)",
                                borderRadius: "var(--radius-md)",
                                border: "1px solid var(--border-primary)",
                                cursor: "pointer",
                                marginBottom: "var(--space-6)",
                                fontSize: "var(--font-sm)",
                                lineHeight: 1.5,
                            }}
                        >
                            <input
                                type="checkbox"
                                checked={consentChecked}
                                onChange={(e) => setConsentChecked(e.target.checked)}
                                style={{
                                    marginTop: 2,
                                    width: 18,
                                    height: 18,
                                    flexShrink: 0,
                                    accentColor: "var(--brand-primary)",
                                }}
                            />
                            <span style={{ color: "var(--text-primary)" }}>
                                I consent to TaxShield processing this notice using AI for the purpose of generating a draft reply. I understand my data rights under the DPDP Act, 2023.
                            </span>
                        </label>

                        {/* Buttons */}
                        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "flex-end" }}>
                            <button
                                className="btn btn-ghost"
                                onClick={() => setShowConsent(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn btn-primary"
                                disabled={!consentChecked}
                                onClick={handleConsentAccept}
                                style={{
                                    opacity: consentChecked ? 1 : 0.5,
                                    cursor: consentChecked ? "pointer" : "not-allowed",
                                }}
                            >
                                <Shield size={16} />
                                Accept & Upload
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
        </AuthGuard>
    );
}
