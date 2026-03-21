"use client";

import { useAuth } from "@/lib/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * AuthGuard — wraps protected pages.
 * Redirects to /login if the user is not authenticated.
 * Shows a loading spinner while auth state is being resolved.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !isAuthenticated) {
            router.replace("/login");
        }
    }, [loading, isAuthenticated, router]);

    if (loading) {
        return (
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "100vh",
                    color: "var(--text-tertiary)",
                    gap: 12,
                }}
            >
                <div
                    style={{
                        width: 20,
                        height: 20,
                        border: "2px solid var(--border-secondary)",
                        borderTopColor: "var(--accent)",
                        borderRadius: "50%",
                        animation: "spin 0.8s linear infinite",
                    }}
                />
                Loading…
            </div>
        );
    }

    if (!isAuthenticated) {
        return null; // Will redirect via useEffect
    }

    return <>{children}</>;
}
