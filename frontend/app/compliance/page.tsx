"use client";

import { useState, useEffect } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { Calendar as CalendarIcon, ShieldAlert, CheckCircle, Clock } from "lucide-react";

interface Notice {
  id: string;
  case_id: string;
  filename: string;
  is_time_barred: boolean;
  response_deadline: string;
  status: string;
}

const API_BASE = "http://localhost:8000";

export default function CompliancePage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/notices?page_size=100`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("taxshield_token") || ""}` },
    })
      .then((r) => r.json())
      .then((data) => {
        const items: Notice[] = Array.isArray(data) ? data : data.items || [];
        // Filter out items without deadlines and sort by deadline ascending
        const withDeadlines = items.filter(n => n.response_deadline);
        withDeadlines.sort((a, b) => new Date(a.response_deadline).getTime() - new Date(b.response_deadline).getTime());
        setNotices(withDeadlines);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <AuthGuard>
         <div className="page-container" style={{ textAlign: "center", paddingTop: "var(--space-16)", color: "var(--text-secondary)" }}>Loading compliance calendar...</div>
      </AuthGuard>
    );
  }

  const upcomingDeadlines = notices.filter(n => new Date(n.response_deadline).getTime() >= Date.now());
  const missedDeadlines = notices.filter(n => new Date(n.response_deadline).getTime() < Date.now());
  const timeBarred = notices.filter(n => n.is_time_barred);

  return (
    <AuthGuard>
      <div className="page-container">
        <h1 className="page-title">Compliance Calendar</h1>
        <p className="page-subtitle">Track Statutory Deadlines to Prevent Ex-Parte Orders and Penalties.</p>

        <div className="stats-grid" style={{ marginBottom: "var(--space-8)" }}>
           <div className="stat-card" style={{ background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
             <div className="stat-card-header">
               <div className="stat-icon-wrapper" style={{ color: "var(--warning)" }}><Clock size={18} /></div>
               <span className="stat-badge" style={{ background: "white", color: "var(--warning)" }}>ACTION REQUIRED</span>
             </div>
             <div className="stat-value" style={{ color: "var(--warning)" }}>{upcomingDeadlines.length}</div>
             <div className="stat-label">Upcoming Deadlines</div>
           </div>
           
           <div className="stat-card" style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
             <div className="stat-card-header">
               <div className="stat-icon-wrapper" style={{ color: "var(--danger)" }}><ShieldAlert size={18} /></div>
               <span className="stat-badge" style={{ background: "white", color: "var(--danger)" }}>CRITICAL</span>
             </div>
             <div className="stat-value" style={{ color: "var(--danger)" }}>{timeBarred.length}</div>
             <div className="stat-label">Time-Barred Defenses Found</div>
           </div>
        </div>

        <div className="data-table-container">
          <div className="data-table-header">
            <div className="data-table-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
               <CalendarIcon size={20} color="var(--brand-primary)" />
               Statutory Deadlines Schedule
            </div>
          </div>
          <div className="table-wrapper">
             <table>
               <thead>
                 <tr>
                    <th>CASE ID</th>
                    <th>RESPONSE DEADLINE</th>
                    <th>TIME-BARRED ARGUMENT</th>
                    <th>STATUS</th>
                 </tr>
               </thead>
               <tbody>
                 {upcomingDeadlines.length > 0 ? upcomingDeadlines.map(n => (
                   <tr key={n.id}>
                     <td style={{ fontWeight: 600 }}>{n.case_id}</td>
                     <td style={{ color: "var(--danger)", fontWeight: 700 }}>{new Date(n.response_deadline).toLocaleDateString("en-IN")}</td>
                     <td>
                        {n.is_time_barred ? (
                           <span className="badge-risk risk-high">Applicable</span>
                        ) : (
                           <span className="badge-risk risk-low">N/A</span>
                        )}
                     </td>
                     <td>
                        {n.status === "processing" ? <span className="badge-status status-review">Processing</span> : <span className="badge-status status-finalized">Ready</span>}
                     </td>
                   </tr>
                 )) : (
                   <tr><td colSpan={4} style={{ textAlign: "center", padding: "var(--space-8)", color: "var(--text-tertiary)" }}>No upcoming deadlines. You are fully compliant!</td></tr>
                 )}
               </tbody>
             </table>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
