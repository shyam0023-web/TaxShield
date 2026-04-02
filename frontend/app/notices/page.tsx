"use client";

import { AuthGuard } from "@/components/AuthGuard";
import { Hammer } from "lucide-react";

export default function NoticesPage() {
  return (
    <AuthGuard>
      <div className="page-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", textAlign: "center" }}>
        <div style={{ background: "var(--bg-secondary)", padding: "var(--space-8)", borderRadius: "var(--radius-xl)", boxShadow: "var(--shadow-lg)", maxWidth: 500, width: "100%" }}>
          <div style={{ width: 80, height: 80, borderRadius: "50%", background: "var(--info-bg)", color: "var(--brand-primary)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto var(--space-6)" }}>
            <Hammer size={40} />
          </div>
          <h1 className="page-title" style={{ marginBottom: "var(--space-2)" }}>All Notices</h1>
          <p className="page-subtitle" style={{ fontSize: "var(--font-base)", marginBottom: 0 }}>
            We're currently building out this detailed grid section. Check the main Dashboard for current notice status!
          </p>
        </div>
      </div>
    </AuthGuard>
  );
}
