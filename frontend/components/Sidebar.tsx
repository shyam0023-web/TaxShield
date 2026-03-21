"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
    LayoutDashboard,
    Upload,
    Settings,
    Shield,
    HelpCircle,
    LogOut,
    LogIn,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/upload", label: "Upload Notice", icon: Upload },
];

const secondaryItems = [
    { href: "#", label: "Settings", icon: Settings },
    { href: "#", label: "Help & Support", icon: HelpCircle },
];

export function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, isAuthenticated, logout } = useAuth();

    const isActive = (href: string) => {
        if (href === "/") return pathname === "/";
        return pathname.startsWith(href);
    };

    const handleLogout = () => {
        logout();
        router.push("/login");
    };

    // Get user initials
    const initials = user?.full_name
        ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
        : "TS";

    return (
        <aside className="sidebar" role="navigation" aria-label="Main navigation">
            <div className="sidebar-brand">
                <div className="sidebar-brand-icon">
                    <Shield size={20} />
                </div>
                <span className="sidebar-brand-text">TaxShield</span>
            </div>

            <nav className="sidebar-nav">
                <div
                    style={{
                        fontSize: "var(--font-xs)",
                        fontWeight: 600,
                        color: "var(--text-tertiary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        padding: "var(--space-3) var(--space-4)",
                        marginBottom: "var(--space-1)",
                    }}
                >
                    Main
                </div>
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`sidebar-link ${isActive(item.href) ? "active" : ""}`}
                    >
                        <item.icon size={18} />
                        {item.label}
                    </Link>
                ))}

                <div style={{ flex: 1 }} />

                <div
                    style={{
                        fontSize: "var(--font-xs)",
                        fontWeight: 600,
                        color: "var(--text-tertiary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        padding: "var(--space-3) var(--space-4)",
                        marginBottom: "var(--space-1)",
                    }}
                >
                    System
                </div>
                {secondaryItems.map((item) => (
                    <Link
                        key={item.label}
                        href={item.href}
                        className="sidebar-link"
                    >
                        <item.icon size={18} />
                        {item.label}
                    </Link>
                ))}
            </nav>

            <div className="sidebar-footer">
                {isAuthenticated && user ? (
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "var(--space-3)",
                            padding: "var(--space-2)",
                        }}
                    >
                        <div
                            style={{
                                width: 32,
                                height: 32,
                                borderRadius: "var(--radius-full)",
                                background: "linear-gradient(135deg, var(--brand-primary), var(--brand-accent))",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: "var(--font-xs)",
                                fontWeight: 600,
                                color: "white",
                                flexShrink: 0,
                            }}
                        >
                            {initials}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div
                                style={{
                                    fontSize: "var(--font-sm)",
                                    fontWeight: 600,
                                    color: "var(--text-primary)",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {user.full_name}
                            </div>
                            <div
                                style={{
                                    fontSize: "var(--font-xs)",
                                    color: "var(--text-tertiary)",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {user.email}
                            </div>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="btn btn-ghost btn-icon"
                            title="Logout"
                            aria-label="Logout"
                            style={{ flexShrink: 0 }}
                        >
                            <LogOut size={16} />
                        </button>
                    </div>
                ) : (
                    <Link
                        href="/login"
                        className="sidebar-link"
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "var(--space-3)",
                            padding: "var(--space-3) var(--space-4)",
                        }}
                    >
                        <LogIn size={18} />
                        Sign In
                    </Link>
                )}
            </div>
        </aside>
    );
}
