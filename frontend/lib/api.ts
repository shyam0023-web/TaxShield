import axios from 'axios';

const API_URL = "http://localhost:8000/api";

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

export async function uploadNotice(file: File, fy: string, section: number): Promise<NoticeResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("fy", fy);
    formData.append("section", section.toString());

    const response = await axios.post(`${API_URL}/upload-notice`, formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    });
    return response.data;
}

export async function sendChatMessage(
    message: string,
    noticeContext: string,
    draftReply: string,
    history: ChatMessage[]
): Promise<ChatResponse> {
    const response = await axios.post(`${API_URL}/chat`, {
        message,
        notice_context: noticeContext,
        draft_reply: draftReply,
        history,
    });
    return response.data;
}
