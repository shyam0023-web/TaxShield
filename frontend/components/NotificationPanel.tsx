"use client";

import { useState, useEffect, useRef } from "react";
import {
    Bell,
    FileCheck,
    Clock,
    AlertTriangle,
    CheckCircle2,
    X,
    Trash2,
} from "lucide-react";

export interface Notification {
    id: string;
    type: "draft_ready" | "deadline" | "approval_pending" | "approved" | "info";
    title: string;
    message: string;
    time: string;
    read: boolean;
    noticeId?: string;
}

const API_BASE = "http://localhost:8000";

const typeConfig = {
    draft_ready: {
        icon: FileCheck,
        color: "var(--info)",
        bg: "var(--info-bg)",
        border: "var(--info-border)",
    },
    deadline: {
        icon: AlertTriangle,
        color: "var(--danger)",
        bg: "var(--danger-bg)",
        border: "var(--danger-border)",
    },
    approval_pending: {
        icon: Clock,
        color: "var(--warning)",
        bg: "var(--warning-bg)",
        border: "var(--warning-border)",
    },
    approved: {
        icon: CheckCircle2,
        color: "var(--success)",
        bg: "var(--success-bg)",
        border: "var(--success-border)",
    },
    info: {
        icon: Bell,
        color: "var(--brand-primary)",
        bg: "var(--info-bg)",
        border: "var(--info-border)",
    },
};

function timeAgo(dateStr: string): string {
    const now = new Date();
    const date = new Date(dateStr);
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays}d ago`;
}

export function NotificationPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const panelRef = useRef<HTMLDivElement>(null);

    // Fetch notifications from backend
    useEffect(() => {
        const fetchNotifications = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/notifications`);
                if (res.ok) {
                    const data = await res.json();
                    setNotifications(Array.isArray(data) ? data : []);
                }
            } catch {
                // Backend not available — empty notifications
            }
        };
        fetchNotifications();
        // Poll every 30 seconds
        const interval = setInterval(fetchNotifications, 30000);
        return () => clearInterval(interval);
    }, []);

    // Close on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };
        if (isOpen) document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [isOpen]);

    // Close on Escape
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") setIsOpen(false);
        };
        if (isOpen) document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, [isOpen]);

    const unreadCount = notifications.filter((n) => !n.read).length;

    const markAsRead = (id: string) => {
        setNotifications((prev) =>
            prev.map((n) => (n.id === id ? { ...n, read: true } : n))
        );
    };

    const markAllRead = () => {
        setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    };

    const clearAll = () => {
        setNotifications([]);
    };

    return (
        <div ref={panelRef} style={{ position: "relative" }}>
            {/* Bell Button */}
            <button
                className="btn btn-ghost btn-icon"
                onClick={() => setIsOpen(!isOpen)}
                aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
                aria-expanded={isOpen}
                aria-haspopup="true"
            >
                <div style={{ position: "relative" }}>
                    <Bell size={20} />
                    {unreadCount > 0 && (
                        <span
                            style={{
                                position: "absolute",
                                top: -4,
                                right: -4,
                                minWidth: 16,
                                height: 16,
                                borderRadius: "var(--radius-full)",
                                background: "var(--danger)",
                                color: "white",
                                fontSize: 10,
                                fontWeight: 700,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                padding: "0 4px",
                                lineHeight: 1,
                            }}
                        >
                            {unreadCount > 9 ? "9+" : unreadCount}
                        </span>
                    )}
                </div>
            </button>

            {/* Dropdown Panel */}
            {isOpen && (
                <div
                    role="dialog"
                    aria-label="Notifications"
                    style={{
                        position: "absolute",
                        top: "calc(100% + 8px)",
                        right: 0,
                        width: 380,
                        maxHeight: 480,
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border-primary)",
                        borderRadius: "var(--radius-lg)",
                        boxShadow: "var(--shadow-lg)",
                        zIndex: 50,
                        display: "flex",
                        flexDirection: "column",
                        overflow: "hidden",
                        animation: "scaleIn 200ms ease-out",
                    }}
                >
                    {/* Header */}
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "var(--space-4) var(--space-5)",
                            borderBottom: "1px solid var(--border-primary)",
                        }}
                    >
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                            <span style={{ fontWeight: 600, fontSize: "var(--font-sm)", color: "var(--text-primary)" }}>
                                Notifications
                            </span>
                            {unreadCount > 0 && (
                                <span
                                    className="badge badge-info"
                                    style={{ fontSize: 10, padding: "2px 6px" }}
                                >
                                    {unreadCount} new
                                </span>
                            )}
                        </div>
                        <div style={{ display: "flex", gap: "var(--space-1)" }}>
                            {notifications.length > 0 && (
                                <>
                                    <button
                                        className="btn btn-ghost"
                                        onClick={markAllRead}
                                        style={{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-2)" }}
                                    >
                                        Mark all read
                                    </button>
                                    <button
                                        className="btn btn-ghost btn-icon"
                                        onClick={clearAll}
                                        aria-label="Clear all notifications"
                                        style={{ padding: "var(--space-1)" }}
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </>
                            )}
                            <button
                                className="btn btn-ghost btn-icon"
                                onClick={() => setIsOpen(false)}
                                aria-label="Close notifications"
                                style={{ padding: "var(--space-1)" }}
                            >
                                <X size={14} />
                            </button>
                        </div>
                    </div>

                    {/* Notification List */}
                    <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-2)" }}>
                        {notifications.length > 0 ? (
                            notifications.map((notification) => {
                                const config = typeConfig[notification.type];
                                const Icon = config.icon;

                                return (
                                    <div
                                        key={notification.id}
                                        onClick={() => markAsRead(notification.id)}
                                        style={{
                                            display: "flex",
                                            gap: "var(--space-3)",
                                            padding: "var(--space-3) var(--space-3)",
                                            borderRadius: "var(--radius-md)",
                                            cursor: "pointer",
                                            background: notification.read ? "transparent" : "var(--bg-surface)",
                                            transition: "background var(--transition-fast)",
                                            marginBottom: "var(--space-1)",
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.background = "var(--bg-surface-hover)";
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.background = notification.read ? "transparent" : "var(--bg-surface)";
                                        }}
                                    >
                                        <div
                                            style={{
                                                width: 32,
                                                height: 32,
                                                borderRadius: "var(--radius-md)",
                                                background: config.bg,
                                                border: `1px solid ${config.border}`,
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "center",
                                                flexShrink: 0,
                                                color: config.color,
                                            }}
                                        >
                                            <Icon size={14} />
                                        </div>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div
                                                style={{
                                                    fontSize: "var(--font-sm)",
                                                    fontWeight: notification.read ? 400 : 600,
                                                    color: "var(--text-primary)",
                                                    marginBottom: 2,
                                                }}
                                            >
                                                {notification.title}
                                            </div>
                                            <div
                                                style={{
                                                    fontSize: "var(--font-xs)",
                                                    color: "var(--text-secondary)",
                                                    lineHeight: 1.4,
                                                    overflow: "hidden",
                                                    textOverflow: "ellipsis",
                                                    whiteSpace: "nowrap",
                                                }}
                                            >
                                                {notification.message}
                                            </div>
                                            <div
                                                style={{
                                                    fontSize: "var(--font-xs)",
                                                    color: "var(--text-tertiary)",
                                                    marginTop: 2,
                                                }}
                                            >
                                                {timeAgo(notification.time)}
                                            </div>
                                        </div>
                                        {!notification.read && (
                                            <div
                                                style={{
                                                    width: 8,
                                                    height: 8,
                                                    borderRadius: "50%",
                                                    background: "var(--brand-primary)",
                                                    flexShrink: 0,
                                                    marginTop: 6,
                                                }}
                                            />
                                        )}
                                    </div>
                                );
                            })
                        ) : (
                            <div
                                style={{
                                    textAlign: "center",
                                    padding: "var(--space-10) var(--space-4)",
                                    color: "var(--text-tertiary)",
                                }}
                            >
                                <Bell size={24} style={{ margin: "0 auto var(--space-3)", opacity: 0.5 }} />
                                <div style={{ fontSize: "var(--font-sm)", fontWeight: 500 }}>
                                    No notifications
                                </div>
                                <div style={{ fontSize: "var(--font-xs)", marginTop: "var(--space-1)" }}>
                                    You&apos;re all caught up
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
