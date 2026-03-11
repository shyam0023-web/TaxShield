"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
    Upload,
    FileText,
    X,
    CheckCircle2,
    AlertCircle,
    CloudUpload,
    File,
    ArrowLeft,
} from "lucide-react";

type UploadStatus = "idle" | "dragging" | "uploading" | "success" | "error";

export default function UploadPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<UploadStatus>("idle");
    const [progress, setProgress] = useState(0);
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
        if (droppedFile && droppedFile.type === "application/pdf") {
            setFile(droppedFile);
            setErrorMessage("");
        } else {
            setErrorMessage("Please upload a PDF file.");
        }
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile && selectedFile.type === "application/pdf") {
            setFile(selectedFile);
            setErrorMessage("");
        } else {
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

            const res = await fetch("http://localhost:8000/api/notices/upload", {
                method: "POST",
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
                throw new Error("Upload failed");
            }
        } catch {
            setStatus("error");
            setProgress(0);
            setErrorMessage("Upload failed. Make sure the backend server is running at http://localhost:8000");
        }
    };

    return (
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
                            onClick={handleUpload}
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
        </>
    );
}
