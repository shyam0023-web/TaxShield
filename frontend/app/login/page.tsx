"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Mail, Lock, User, LogIn, UserPlus, AlertCircle, Loader2 } from "lucide-react";
import { loginUser, registerUser } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

export default function LoginPage() {
    const router = useRouter();
    const { login } = useAuth();
    const [isRegister, setIsRegister] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [fullName, setFullName] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            let result;
            if (isRegister) {
                if (!fullName.trim()) {
                    setError("Full name is required");
                    setLoading(false);
                    return;
                }
                result = await registerUser(email, password, fullName);
            } else {
                result = await loginUser(email, password);
            }
            login(result.token, result.user);
            router.push("/");
        } catch (err: any) {
            setError(err.message || "Something went wrong");
        } finally {
            setLoading(false);
        }
    };

    const inputStyle: React.CSSProperties = {
        width: "100%",
        padding: "12px 16px 12px 44px",
        fontSize: "var(--font-sm)",
        background: "var(--bg-tertiary)",
        border: "1px solid var(--border-secondary)",
        borderRadius: "var(--radius-md)",
        color: "var(--text-primary)",
        outline: "none",
        transition: "border-color 0.2s",
    };

    const iconStyle: React.CSSProperties = {
        position: "absolute",
        left: 14,
        top: "50%",
        transform: "translateY(-50%)",
        color: "var(--text-tertiary)",
        pointerEvents: "none",
    };

    return (
        <div style={{
            minHeight: "100dvh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--bg-primary)",
            padding: "var(--space-6)",
        }}>
            <div style={{
                width: "100%",
                maxWidth: 420,
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-xl)",
                border: "1px solid var(--border-primary)",
                padding: "var(--space-8)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
            }}>
                {/* Logo */}
                <div style={{ textAlign: "center", marginBottom: "var(--space-8)" }}>
                    <div style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 56,
                        height: 56,
                        borderRadius: "var(--radius-lg)",
                        background: "linear-gradient(135deg, var(--brand-primary), var(--brand-secondary, #6366f1))",
                        marginBottom: "var(--space-4)",
                    }}>
                        <Shield size={28} style={{ color: "white" }} />
                    </div>
                    <h1 style={{
                        fontSize: "var(--font-xl)",
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        margin: 0,
                    }}>
                        TaxShield
                    </h1>
                    <p style={{
                        fontSize: "var(--font-sm)",
                        color: "var(--text-tertiary)",
                        marginTop: "var(--space-2)",
                    }}>
                        {isRegister ? "Create your account" : "Sign in to your account"}
                    </p>
                </div>

                {/* Error */}
                {error && (
                    <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "var(--space-2)",
                        padding: "var(--space-3) var(--space-4)",
                        background: "rgba(239,68,68,0.1)",
                        border: "1px solid rgba(239,68,68,0.3)",
                        borderRadius: "var(--radius-md)",
                        marginBottom: "var(--space-5)",
                        color: "#ef4444",
                        fontSize: "var(--font-sm)",
                    }}>
                        <AlertCircle size={16} />
                        {error}
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit}>
                    {isRegister && (
                        <div style={{ position: "relative", marginBottom: "var(--space-4)" }}>
                            <User size={18} style={iconStyle} />
                            <input
                                type="text"
                                placeholder="Full Name"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                style={inputStyle}
                                required
                                autoComplete="name"
                            />
                        </div>
                    )}
                    <div style={{ position: "relative", marginBottom: "var(--space-4)" }}>
                        <Mail size={18} style={iconStyle} />
                        <input
                            type="email"
                            placeholder="Email address"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            style={inputStyle}
                            required
                            autoComplete="email"
                        />
                    </div>
                    <div style={{ position: "relative", marginBottom: "var(--space-6)" }}>
                        <Lock size={18} style={iconStyle} />
                        <input
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={inputStyle}
                            required
                            minLength={6}
                            autoComplete={isRegister ? "new-password" : "current-password"}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn btn-primary"
                        style={{
                            width: "100%",
                            padding: "12px",
                            fontSize: "var(--font-sm)",
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "var(--space-2)",
                            opacity: loading ? 0.7 : 1,
                        }}
                    >
                        {loading ? (
                            <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
                        ) : isRegister ? (
                            <UserPlus size={18} />
                        ) : (
                            <LogIn size={18} />
                        )}
                        {loading ? "Please wait..." : isRegister ? "Create Account" : "Sign In"}
                    </button>
                </form>

                {/* Toggle */}
                <div style={{
                    textAlign: "center",
                    marginTop: "var(--space-6)",
                    fontSize: "var(--font-sm)",
                    color: "var(--text-tertiary)",
                }}>
                    {isRegister ? "Already have an account?" : "Don\u2019t have an account?"}{" "}
                    <button
                        type="button"
                        onClick={() => { setIsRegister(!isRegister); setError(""); }}
                        style={{
                            background: "none",
                            border: "none",
                            color: "var(--brand-primary)",
                            cursor: "pointer",
                            fontWeight: 600,
                            fontSize: "inherit",
                            padding: 0,
                        }}
                    >
                        {isRegister ? "Sign In" : "Create Account"}
                    </button>
                </div>

                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
        </div>
    );
}
