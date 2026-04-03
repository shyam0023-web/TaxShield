"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, Settings, User } from "lucide-react";
import { NotificationPanel } from "./NotificationPanel";
import { useAuth } from "@/lib/AuthContext";

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, user } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
      logout();
      router.push("/login");
  };
  const navLinks = [
    { name: "Dashboard", href: "/" },
    { name: "Notices", href: "/notices" },
    { name: "Reports", href: "/reports" },
    { name: "Drafts", href: "/drafts" },
  ];

  return (
    <header className="top-header">
      <nav className="header-nav">
        {navLinks.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={isActive ? "active" : ""}
            >
              {link.name}
            </Link>
          );
        })}
      </nav>

      <div className="header-actions">
        <NotificationPanel />
        <button className="btn-icon">
          <Settings size={20} />
        </button>
        <div style={{ position: "relative" }} ref={menuRef}>
          <button className="btn-icon" onClick={() => setShowUserMenu(!showUserMenu)} aria-label="Account menu">
            <User size={20} />
          </button>
          {showUserMenu && (
            <div style={{
              position: "absolute",
              top: "100%",
              right: 0,
              marginTop: "var(--space-2)",
              backgroundColor: "var(--bg-primary)",
              border: "1px solid var(--border-secondary)",
              borderRadius: "var(--radius-md)",
              boxShadow: "var(--shadow-md)",
              padding: "var(--space-2)",
              minWidth: "180px",
              zIndex: 50,
            }}>
              {user && (
                  <div style={{ padding: "var(--space-2)", borderBottom: "1px solid var(--border-secondary)", marginBottom: "var(--space-2)" }}>
                      <p style={{ margin: 0, fontWeight: 600, fontSize: "var(--font-sm)", color: "var(--text-primary)" }}>{user.full_name}</p>
                      <p style={{ margin: 0, fontSize: "var(--font-xs)", color: "var(--text-tertiary)", wordBreak: "break-all" }}>{user.email}</p>
                  </div>
              )}
              <button 
                onClick={handleLogout}
                style={{
                  width: "100%",
                  padding: "var(--space-2)",
                  textAlign: "left",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                  fontSize: "var(--font-sm)",
                  borderRadius: "var(--radius-sm)",
                  transition: "background-color 0.2s"
                }}
                onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-secondary)")}
                onMouseOut={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
              >
                Log Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
