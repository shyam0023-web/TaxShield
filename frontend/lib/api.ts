/**
 * TaxShield — API Client
 * Central API client for all backend communication.
 * Uses native fetch (no axios dependency needed).
 */

const API_BASE = "http://localhost:8000/api";

// ═══════════════════════════════════════════
// Auth helpers
// ═══════════════════════════════════════════

export function getAuthHeaders(): Record<string, string> {
    const token = typeof window !== "undefined" ? localStorage.getItem("taxshield_token") : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
}

/** POST /api/auth/login */
export async function loginUser(email: string, password: string): Promise<{ token: string; user: { id: string; email: string; full_name: string; role: string } }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Login failed");
    }
    return res.json();
}

/** POST /api/auth/register */
export async function registerUser(email: string, password: string, fullName: string): Promise<{ token: string; user: { id: string; email: string; full_name: string; role: string } }> {
    const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Registration failed");
    }
    return res.json();
}

// ═══════════════════════════════════════════
// Types matching backend response shapes
// ═══════════════════════════════════════════

/** POST /api/notices/upload response */
export interface UploadResponse {
    id: string;
    case_id: string;
    risk_level: string;
    status: string;
    draft_status: string;
}

/** GET /api/notices list item */
export interface NoticeSummary {
    id: string;
    case_id: string;
    filename: string;
    notice_type: string;
    fy: string;
    section: string;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
    demand_amount: number;
    response_deadline: string;
    draft_status: string;
    status: string;
    is_time_barred: boolean;
    created_at: string;
}

/** GET /api/notices/{id} detail */
export interface NoticeDetail {
    id: string;
    case_id: string;
    filename: string;
    notice_text: string;
    entities: Record<string, any>;
    notice_annotations: any[];
    processing_status: string;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
    risk_score: number;
    risk_reasoning: string;
    is_time_barred: boolean;
    time_bar_detail: Record<string, any>;
    fy: string;
    section: string;
    notice_type: string;
    demand_amount: number;
    response_deadline: string;
    draft_reply: string;
    draft_status: string;
    verification_status: string | null;
    verification_score: number | null;
    verification_issues: Array<{ stage: string; issue: string; severity: string; location: string; suggestion: string }>;
    accuracy_report: Record<string, any>;
    status: string;
    error_message: string | null;
    created_at: string;
    updated_at: string;
}

/** GET /api/notifications item */
export interface Notification {
    id: string;
    type: "draft_ready" | "deadline" | "approval_pending" | "approved" | "info";
    title: string;
    message: string;
    time: string;
    read: boolean;
    noticeId?: string;
}

// Legacy type kept for UploadNotice.tsx compatibility
export interface NoticeResponse {
    extracted_text: string;
    reply: string;
    audit_passed: boolean;
    confidence: number;
    relevant_laws: string[];
}

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
}

export interface ChatResponse {
    reply: string;
    sources: string[];
}

// ═══════════════════════════════════════════
// API Functions
// ═══════════════════════════════════════════

/** Upload a PDF notice for processing */
export async function uploadNotice(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/notices/upload`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || `Upload failed (${res.status})`);
    }

    return res.json();
}

/** Paginated response from GET /api/notices */
export interface PaginatedNotices {
    items: NoticeSummary[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

/** Fetch notices with pagination */
export async function fetchNotices(page = 1, pageSize = 20): Promise<PaginatedNotices> {
    const res = await fetch(`${API_BASE}/notices?page=${page}&page_size=${pageSize}`, {
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch notices");
    return res.json();
}

/** Fetch a single notice by ID */
export async function fetchNotice(id: string): Promise<NoticeDetail> {
    const res = await fetch(`${API_BASE}/notices/${id}`, {
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Notice not found");
    return res.json();
}

/** Fetch notifications for the bell icon */
export async function fetchNotifications(): Promise<Notification[]> {
    const res = await fetch(`${API_BASE}/notifications`);
    if (!res.ok) return [];
    return res.json();
}

/** DELETE /api/notices/{id} — DPDP Right to Erasure */
export async function deleteNotice(id: string): Promise<{ deleted: boolean; case_id: string }> {
    const res = await fetch(`${API_BASE}/notices/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete notice");
    return res.json();
}

/** POST /api/notices/{id}/approve */
export async function approveDraft(id: string, feedback?: string): Promise<{ draft_status: string }> {
    const res = await fetch(`${API_BASE}/notices/${id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ feedback: feedback || null }),
    });
    if (!res.ok) throw new Error("Failed to approve draft");
    return res.json();
}

/** POST /api/notices/{id}/reject */
export async function rejectDraft(id: string, feedback?: string): Promise<{ draft_status: string }> {
    const res = await fetch(`${API_BASE}/notices/${id}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ feedback: feedback || null }),
    });
    if (!res.ok) throw new Error("Failed to reject draft");
    return res.json();
}

/** PUT /api/notices/{id}/draft */
export async function updateDraft(id: string, draftReply: string): Promise<{ draft_status: string; draft_reply: string }> {
    const res = await fetch(`${API_BASE}/notices/${id}/draft`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ draft_reply: draftReply }),
    });
    if (!res.ok) throw new Error("Failed to update draft");
    return res.json();
}

/** Send a chat message (for future Agent 3 WebSocket integration) */
export async function sendChatMessage(
    message: string,
    noticeContext: string,
    draftReply: string,
    history: ChatMessage[]
): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message,
            notice_context: noticeContext,
            draft_reply: draftReply,
            history,
        }),
    });

    if (!res.ok) throw new Error("Chat request failed");
    return res.json();
}
