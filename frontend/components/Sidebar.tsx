"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PieChart,
  ClipboardList,
  ShieldCheck,
  History,
} from "lucide-react";
import { NotificationPanel } from "./NotificationPanel";

export function Sidebar() {
  const pathname = usePathname();

  const links = [
    { name: "OVERVIEW", icon: LayoutDashboard, href: "/" },
    { name: "ANALYTICS", icon: PieChart, href: "/analytics" },
    { name: "AUDIT LOG", icon: ClipboardList, href: "/audit" },
    { name: "COMPLIANCE", icon: ShieldCheck, href: "/compliance" },
    { name: "HISTORY", icon: History, href: "/history" },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-text">TaxShield</span>
      </div>

      <nav className="sidebar-nav">
        {links.map((link) => {
          const isActive = pathname === link.href;
          const Icon = link.icon;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={`sidebar-link ${isActive ? "active" : ""}`}
            >
              <Icon size={18} strokeWidth={2.5} />
              {link.name}
            </Link>
          );
        })}
      </nav>

      <div style={{ padding: "var(--space-6)", marginTop: "auto" }}>
        <Link href="/upload" className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }}>
          Upload Notice
        </Link>
      </div>
    </aside>
  );
}
