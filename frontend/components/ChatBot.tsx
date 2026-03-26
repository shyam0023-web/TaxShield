"use client";

import { useState, useRef, useEffect } from "react";
import { uploadNotice, sendChatMessage, UploadResponse, ChatMessage } from "@/lib/api";

interface Message {
    role: "user" | "assistant" | "system";
    content: string;
    type?: "text" | "upload" | "result";
    result?: UploadResponse;
    sources?: string[];
}

export default function ChatBot() {
    const [messages, setMessages] = useState<Message[]>([
        {
            role: "assistant",
            content: "👋 Welcome to **TaxShield**! I'm your GST legal assistant.\n\nYou can:\n• Upload a GST notice PDF for analysis\n• Ask me any GST-related questions\n\nHow can I help you today?",
            type: "text",
        },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [noticeContext, setNoticeContext] = useState("");
    const [draftReply, setDraftReply] = useState("");
    const fileInputRef = useRef<HTMLInputElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0];
        if (selected) {
            setFile(selected);
        }
    };

    const handleSend = async () => {
        if (loading) return;
        if (!input.trim() && !file) return;

        if (file) {
            await handleUpload();
        } else {
            await handleChat();
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        const userMsg: Message = {
            role: "user",
            content: `📎 Uploaded **${file.name}** for analysis (FY 2024-25, Section 73)`,
            type: "upload",
        };
        setMessages((prev) => [...prev, userMsg]);
        setLoading(true);

        try {
            const data = await uploadNotice(file);
            setNoticeContext(data.case_id);
            setDraftReply(data.draft_status);

            const resultMsg: Message = {
                role: "assistant",
                content: `✅ Notice **${data.case_id}** analyzed!\n\n• Risk: **${data.risk_level}**\n• Draft: **${data.draft_status === "draft_ready" ? "Ready" : "Pending"}**\n\nYou can ask me follow-up questions about this notice.`,
                type: "text",
            };
            setMessages((prev) => [...prev, resultMsg]);
        } catch {
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "❌ Failed to analyze the PDF. Please make sure your backend is running.", type: "text" },
            ]);
        } finally {
            setFile(null);
            if (fileInputRef.current) fileInputRef.current.value = "";
            setLoading(false);
        }
    };

    const handleChat = async () => {
        const text = input.trim();
        if (!text) return;

        const userMsg: Message = { role: "user", content: text, type: "text" };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        const chatHistory: ChatMessage[] = messages
            .filter((m) => m.type === "text" && (m.role === "user" || m.role === "assistant"))
            .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));

        try {
            const response = await sendChatMessage(text, noticeContext, draftReply, chatHistory);
            setMessages((prev) => [...prev, { role: "assistant", content: response.reply, type: "text", sources: response.sources || [] }]);
        } catch {
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "Sorry, I encountered an error. Please try again.", type: "text" },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-screen gradient-bg">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 border-b border-white/10 backdrop-blur-lg bg-white/5">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="text-lg font-semibold text-white">TaxShield</h1>
                        <p className="text-xs text-gray-400">GST Legal Assistant</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-xs text-gray-400">Online</span>
                </div>
            </header>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
                <div className="max-w-3xl mx-auto space-y-4">
                    {messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                            {msg.role === "assistant" && (
                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mr-3 mt-1 flex-shrink-0">
                                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                    </svg>
                                </div>
                            )}

                            <div className={`max-w-[75%] ${msg.role === "user" ? "" : ""}`}>
                                {msg.type === "result" && msg.result ? (
                                    <div style={{ padding: "var(--space-5)", background: "var(--bg-surface)", border: "1px solid var(--border-primary)", borderRadius: "var(--radius-lg)" }}>
                                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-3)" }}>
                                            <span style={{ fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)" }}>📊 Analysis Result</span>
                                            <span className={`badge badge-${msg.result.risk_level?.toLowerCase() || "low"}`}>
                                                {msg.result.risk_level} Risk
                                            </span>
                                        </div>
                                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
                                            <div style={{ padding: "var(--space-3)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>Status</div>
                                                <div style={{ fontSize: "var(--font-base)", fontWeight: 600, color: "var(--text-primary)" }}>{msg.result.status}</div>
                                            </div>
                                            <div style={{ padding: "var(--space-3)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-secondary)" }}>
                                                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>Draft</div>
                                                <div style={{ fontSize: "var(--font-base)", fontWeight: 600, color: "var(--text-primary)" }}>
                                                    {msg.result.draft_status === "draft_ready" ? "✅ Ready" : "⏳ Pending"}
                                                </div>
                                            </div>
                                        </div>
                                        <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", marginTop: "var(--space-3)" }}>💬 You can now ask me follow-up questions about this notice.</div>
                                    </div>
                                ) : (
                                    <div>
                                        <div
                                            className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${msg.role === "user"
                                                ? "bg-indigo-500/30 text-indigo-100 border border-indigo-500/30 rounded-br-md"
                                                : "bg-white/5 text-gray-200 border border-white/10 rounded-bl-md"
                                                }`}
                                        >
                                            {msg.content}
                                        </div>
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="flex flex-wrap gap-1.5 mt-2">
                                                <span className="text-xs text-gray-500">Sources:</span>
                                                {msg.sources.map((src, j) => (
                                                    <span key={j} className="bg-indigo-500/15 text-indigo-400 px-2.5 py-0.5 rounded-full text-xs border border-indigo-500/20">
                                                        {src}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {msg.role === "user" && (
                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center ml-3 mt-1 flex-shrink-0">
                                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                    </svg>
                                </div>
                            )}
                        </div>
                    ))}

                    {loading && (
                        <div className="flex justify-start">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mr-3 flex-shrink-0">
                                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                            </div>
                            <div className="bg-white/5 border border-white/10 px-4 py-3 rounded-2xl rounded-bl-md">
                                <div className="flex gap-1.5">
                                    <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                                    <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                                    <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* File Preview */}
            {file && (
                <div className="max-w-3xl mx-auto w-full px-4">
                    <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl px-4 py-3 flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                            <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            <span className="text-sm text-indigo-300">{file.name}</span>
                        </div>
                        <button
                            onClick={() => {
                                setFile(null);
                                if (fileInputRef.current) fileInputRef.current.value = "";
                            }}
                            className="text-gray-400 hover:text-white transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            )}

            {/* Input Area */}
            <div className="border-t border-white/10 backdrop-blur-lg bg-white/5 px-4 py-4">
                <div className="max-w-3xl mx-auto flex items-center gap-3">
                    <input type="file" ref={fileInputRef} accept=".pdf" onChange={handleFileSelect} className="hidden" />

                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="w-11 h-11 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors flex-shrink-0"
                        title="Upload PDF"
                    >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                        </svg>
                    </button>

                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={file ? "Press Send to analyze PDF..." : "Ask about GST, upload a notice..."}
                        className="flex-1 input-dark rounded-xl px-4 py-3 text-sm"
                        disabled={loading}
                    />

                    <button
                        onClick={handleSend}
                        disabled={(!input.trim() && !file) || loading}
                        className="w-11 h-11 btn-primary rounded-xl flex items-center justify-center flex-shrink-0"
                    >
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
