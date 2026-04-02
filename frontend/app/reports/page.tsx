"use client";

import { AuthGuard } from "@/components/AuthGuard";
import { Download, FileBarChart, PieChart, ShieldAlert } from "lucide-react";

export default function ReportsPage() {
  return (
    <AuthGuard>
      <div className="page-container">
        <h1 className="page-title">MIS Reports</h1>
        <p className="page-subtitle">Generate and download compiled compliance reports for internal auditing and management review.</p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: "var(--space-6)", marginTop: "var(--space-8)" }}>
          
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
               <div style={{ width: 44, height: 44, background: "var(--brand-primary-glow)", color: "var(--brand-primary)", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                 <FileBarChart size={24} />
               </div>
               <div>
                 <h3 style={{ fontSize: "var(--font-lg)", fontWeight: 700, color: "var(--text-primary)" }}>Monthly Compliance Summary</h3>
                 <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>PDF · Generated End-of-Month</p>
               </div>
            </div>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>Aggregated summary of all notices processed, AI drafts finalized, and total exposure mitigated.</p>
            <button className="btn btn-outline" style={{ width: "100%", justifyContent: "center", marginTop: "auto" }}>
              <Download size={16} /> Download Latest Report
            </button>
          </div>

          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
               <div style={{ width: 44, height: 44, background: "var(--danger-bg)", color: "var(--danger)", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                 <ShieldAlert size={24} />
               </div>
               <div>
                 <h3 style={{ fontSize: "var(--font-lg)", fontWeight: 700, color: "var(--text-primary)" }}>High-Risk Exposure Analysis</h3>
                 <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Excel (CSV) · Real-time</p>
               </div>
            </div>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>Extract pure data for all high-risk notices, including demand amounts and statutory deadlines for risk mitigation.</p>
            <button className="btn btn-outline" style={{ width: "100%", justifyContent: "center", marginTop: "auto" }}>
              <Download size={16} /> Export to CSV
            </button>
          </div>

          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
               <div style={{ width: 44, height: 44, background: "var(--info-bg)", color: "var(--info)", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                 <PieChart size={24} />
               </div>
               <div>
                 <h3 style={{ fontSize: "var(--font-lg)", fontWeight: 700, color: "var(--text-primary)" }}>Algorithm Accuracy Metrics</h3>
                 <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>JSON / PDF · Real-time</p>
               </div>
            </div>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)" }}>Detailed AI processing logs, LLM token usage, and user-override frequency used for algorithm auditing.</p>
            <button className="btn btn-outline" style={{ width: "100%", justifyContent: "center", marginTop: "auto" }}>
              <Download size={16} /> Retrieve Diagnostic Log
            </button>
          </div>

        </div>
      </div>
    </AuthGuard>
  );
}
