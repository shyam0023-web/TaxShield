import axios from 'axios';

const API_URL = "http://localhost:8000/api";

export interface NoticeResponse {
  extracted_text: string;
  reply: string;
  audit_passed: boolean;
  confidence: number;
}

export async function uploadNotice(file: File, fy: string, section: number) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("fy", fy);
  formData.append("section", section.toString());
  
  try {
    const response = await axios.post(`${API_URL}/upload-notice`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data as NoticeResponse;
  } catch (error) {
    console.error("Upload failed", error);
    throw error;
  }
}
