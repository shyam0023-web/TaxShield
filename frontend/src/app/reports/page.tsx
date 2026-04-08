'use client';

import { useState, useEffect } from 'react';
import { FileText, Download, Copy, Share2, Loader } from 'lucide-react';
import ReportChat from '../../components/ReportChat';

interface Report {
  id: string;
  documentId: string;
  type: string;
  title: string;
  content: string;
  generatedAt: string;
  lastUpdatedAt?: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingReport, setEditingReport] = useState<string | null>(null);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/reports');
      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || data);
        if (data.reports && data.reports.length > 0) {
          setSelectedReport(data.reports[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch reports:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReportUpdate = (updatedReport: string) => {
    if (selectedReport) {
      const updated = {
        ...selectedReport,
        content: updatedReport,
        lastUpdatedAt: new Date().toISOString(),
      };
      setSelectedReport(updated);
      setReports((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
      setEditingReport(null);
    }
  };

  const handleCopyReport = () => {
    if (selectedReport) {
      navigator.clipboard.writeText(selectedReport.content);
      setCopiedId(selectedReport.id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const handleDownloadReport = () => {
    if (selectedReport) {
      const element = document.createElement('a');
      const file = new Blob([selectedReport.content], {
        type: 'text/plain',
      });
      element.href = URL.createObjectURL(file);
      element.download = `${selectedReport.title.replace(/\s+/g, '_')}.txt`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <FileText className="text-blue-600" size={32} />
            <h1 className="text-4xl font-bold text-slate-900">Reports</h1>
          </div>
          <p className="text-slate-600">
            Generated analysis and defense strategies with AI refinement
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Reports List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-200 bg-slate-50">
                <h2 className="font-semibold text-slate-900">Your Reports</h2>
                <p className="text-xs text-slate-500 mt-1">{reports.length} total</p>
              </div>

              <div className="divide-y divide-slate-200 max-h-96 overflow-y-auto">
                {isLoading ? (
                  <div className="p-4 flex items-center justify-center">
                    <Loader size={20} className="animate-spin text-slate-400" />
                  </div>
                ) : reports.length === 0 ? (
                  <div className="p-4 text-center text-slate-500 text-sm">
                    No reports yet. Upload a notice to generate one.
                  </div>
                ) : (
                  reports.map((report) => (
                    <button
                      key={report.id}
                      onClick={() => setSelectedReport(report)}
                      className={`w-full text-left p-4 hover:bg-slate-50 transition-colors ${
                        selectedReport?.id === report.id
                          ? 'bg-blue-50 border-l-4 border-l-blue-600'
                          : ''
                      }`}
                    >
                      <h3 className="font-medium text-slate-900 truncate">
                        {report.title}
                      </h3>
                      <p className="text-xs text-slate-500 mt-1">
                        {new Date(report.generatedAt).toLocaleDateString()}
                      </p>
                      <span className="inline-block mt-2 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                        {report.type}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Report Viewer and Chat */}
          <div className="lg:col-span-3">
            {selectedReport ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Report Content */}
                <div className="bg-white rounded-lg shadow-md border border-slate-200 overflow-hidden flex flex-col">
                  <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                    <div className="flex items-start justify-between">
                      <div>
                        <h2 className="text-2xl font-bold text-slate-900">
                          {selectedReport.title}
                        </h2>
                        <p className="text-sm text-slate-600 mt-1">
                          Generated:{' '}
                          {new Date(
                            selectedReport.lastUpdatedAt ||
                              selectedReport.generatedAt
                          ).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={handleCopyReport}
                          title="Copy report"
                          className="p-2 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors"
                        >
                          <Copy size={20} />
                        </button>
                        <button
                          onClick={handleDownloadReport}
                          title="Download report"
                          className="p-2 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors"
                        >
                          <Download size={20} />
                        </button>
                        <button
                          title="Share report"
                          className="p-2 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors"
                        >
                          <Share2 size={20} />
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 p-6 overflow-y-auto prose prose-sm max-w-none">
                    <div className="whitespace-pre-wrap text-slate-700 leading-relaxed text-sm">
                      {selectedReport.content}
                    </div>
                  </div>
                </div>

                {/* AI Chat Refinement */}
                <ReportChat
                  reportId={selectedReport.id}
                  documentId={selectedReport.documentId}
                  currentReport={selectedReport.content}
                  onReportUpdate={handleReportUpdate}
                  isLoadingReport={isLoading}
                />
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-md border border-slate-200 p-12 text-center">
                <FileText size={48} className="mx-auto text-slate-300 mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  No Report Selected
                </h3>
                <p className="text-slate-600">
                  Select a report from the list to view and refine it with AI
                  suggestions
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Tips */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-semibold text-blue-900 mb-3">💡 AI Refinement Tips</h3>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-800">
            <li>• Ask for specific improvements: "Make the defense stronger"</li>
            <li>• Request better legal citations: "Add more relevant sections"</li>
            <li>• Suggest tone changes: "Make it more formal"</li>
            <li>• Request additional analysis: "Expand on compliance issues"</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
