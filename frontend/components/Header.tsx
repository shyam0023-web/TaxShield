"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Settings, User } from "lucide-react";
import { NotificationPanel } from "./NotificationPanel";

export function Header() {
  const pathname = usePathname();

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
        <button className="btn-icon">
          <User size={20} />
        </button>
      </div>
    </header>
  );
}
