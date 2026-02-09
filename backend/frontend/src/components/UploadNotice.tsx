"use client";
import { useState } from "react";
import { uploadNotice, NoticeResponse } from "@/lib/api";

export default function UploadNotice() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NoticeResponse | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    try {
      // Hardcoded FY/Section for now (we can add inputs later)
      const data = await uploadNotice(file, "2024-25", 73);
      setResult(data);
    } catch (error) {
      alert("Failed to analyze notice");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-6 max-w-4xl mx-auto p-4">
      {/* Upload Card */}
      <div className="w-1/2 bg-white rounded-lg shadow-md border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Upload GST Notice</h2>
        </div>
        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Select PDF File
            </label>
            <input 
              type="file" 
              accept=".pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          <button 
            onClick={handleUpload} 
            disabled={!file || loading} 
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing...
              </>
            ) : "Analyze Notice"}
          </button>
        </div>
      </div>

      {/* Result Card */}
      {result && (
        <div className="w-1/2 bg-slate-50 rounded-lg shadow-md border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-green-700">Analysis Complete</h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="text-sm font-semibold">
              Audit Passed: {result.audit_passed ? "✅ Yes" : "❌ No"}
            </div>
            <div className="text-sm">
              Confidence: {(result.confidence * 100).toFixed(0)}%
            </div>
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                AI Analysis Response:
              </label>
              <textarea 
                className="w-full h-64 p-3 border border-gray-300 rounded-md text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={result.reply}
                readOnly
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
