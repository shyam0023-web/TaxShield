"use client";

import { useState } from "react";
import { uploadNotice, NoticeResponse } from "@/lib/api";

export default function UploadNotice() {
    const [file, setFile] = useState<File | null>(null);
    const [fy, setFy] = useState("2024-25");
    const [section, setSection] = useState(73);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<NoticeResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        setError(null);
        try {
            const data = await uploadNotice(file, fy, section);
            setResult(data);
        } catch (err: any) {
            setError(err.message || "Failed to analyze notice");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="grid lg:grid-cols-2 gap-8">
            {/* Upload Card */}
            <div className="glass-card p-8 relative overflow-hidden">
                <div className="floating-orb w-32 h-32 bg-indigo-500 -top-16 -right-16" />

                <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-white">Upload Notice</h2>
                            <p className="text-sm text-gray-400">PDF files supported</p>
                        </div>
                    </div>

                    <div className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">GST Notice Document</label>
                            <input
                                type="file"
                                accept=".pdf"
                                onChange={(e) => setFile(e.target.files?.[0] || null)}
                                className="w-full input-dark rounded-xl p-4 text-sm cursor-pointer"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Financial Year</label>
                                <select
                                    value={fy}
                                    onChange={(e) => setFy(e.target.value)}
                                    className="w-full input-dark rounded-xl p-4 text-sm"
                                >
                                    <option value="2024-25">FY 2024-25</option>
                                    <option value="2023-24">FY 2023-24</option>
                                    <option value="2022-23">FY 2022-23</option>
                                    <option value="2021-22">FY 2021-22</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Section</label>
                                <select
                                    value={section}
                                    onChange={(e) => setSection(Number(e.target.value))}
                                    className="w-full input-dark rounded-xl p-4 text-sm"
                                >
                                    <option value={73}>Section 73</option>
                                    <option value={74}>Section 74</option>
                                </select>
                            </div>
                        </div>

                        <button
                            onClick={handleUpload}
                            disabled={!file || loading}
                            className="w-full btn-primary text-white font-semibold py-4 px-6 rounded-xl flex items-center justify-center gap-3"
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    <span>Analyzing with AI...</span>
                                </>
                            ) : (
                                <>
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                    <span>Analyze Notice</span>
                                </>
                            )}
                        </button>

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl text-sm flex items-center gap-3">
                                <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {error}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Result Card */}
            {result ? (
                <div className="glass-card p-8 glow-border relative overflow-hidden">
                    <div className="floating-orb w-40 h-40 bg-purple-500 -bottom-20 -right-20" />

                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </div>
                                <div>
                                    <h2 className="text-xl font-semibold text-white">Analysis Complete</h2>
                                    <p className="text-sm text-gray-400">AI-generated response ready</p>
                                </div>
                            </div>
                            <span className={`status-badge ${result.audit_passed ? 'status-success' : 'status-warning'}`}>
                                {result.audit_passed ? "✓ Verified" : "⚠ Review Needed"}
                            </span>
                        </div>

                        <div className="space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                                    <div className="text-sm text-gray-400 mb-1">Confidence Score</div>
                                    <div className="text-2xl font-bold gradient-text">{(result.confidence * 100).toFixed(0)}%</div>
                                </div>
                                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                                    <div className="text-sm text-gray-400 mb-1">Citations Found</div>
                                    <div className="text-2xl font-bold gradient-text">{result.relevant_laws.length}</div>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Generated Legal Reply</label>
                                <textarea
                                    className="w-full h-64 p-4 textarea-dark rounded-xl text-sm resize-none"
                                    value={result.reply}
                                    readOnly
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-3">Referenced Circulars</label>
                                <div className="flex flex-wrap gap-2">
                                    {result.relevant_laws.map((law, i) => (
                                        <span key={i} className="bg-indigo-500/20 text-indigo-300 px-4 py-2 rounded-full text-sm border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors cursor-default">
                                            📄 {law}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="glass-card p-8 flex flex-col items-center justify-center text-center min-h-[400px]">
                    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center mb-6">
                        <svg className="w-10 h-10 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">Ready to Analyze</h3>
                    <p className="text-gray-400 max-w-sm">
                        Upload a GST notice PDF to get an AI-powered legal response with relevant law citations
                    </p>
                </div>
            )}
        </div>
    );
}
