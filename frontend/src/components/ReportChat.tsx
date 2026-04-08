'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader, RefreshCw } from 'lucide-react';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ReportChatProps {
  reportId: string;
  documentId: string;
  currentReport: string;
  onReportUpdate: (updatedReport: string) => void;
  isLoadingReport?: boolean;
}

export default function ReportChat({
  reportId,
  documentId,
  currentReport,
  onReportUpdate,
  isLoadingReport = false,
}: ReportChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Debug: log mount and props to help diagnose visibility issues
  useEffect(() => {
    // This will appear in the browser console when the component mounts
    try {
      // eslint-disable-next-line no-console
      console.log('ReportChat mounted', { reportId, documentId });
    } catch (e) {
      /* ignore */
    }
  }, [reportId, documentId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: '0',
          type: 'assistant',
          content: `I can help you refine this report with AI suggestions. You can:
          
• Ask me to modify specific sections
• Request better legal arguments
• Suggest stronger compliance strategies
• Ask for more detailed analysis
• Request tone or language changes

What would you like to improve?`,
          timestamp: new Date(),
        },
      ]);
    }
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Call backend API to refine report based on suggestion
      const response = await fetch('/api/reports/refine', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          documentId,
          reportId,
          currentReport,
          suggestion: input,
        }),
      });

      if (!response.ok) throw new Error('Failed to refine report');

      const data = await response.json();
      const refinedReport = data.refinedReport || data.updatedReport;

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.explanation || 'Report updated with your suggestions.',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Update the parent report
      if (refinedReport) {
        onReportUpdate(refinedReport);
      }
    } catch (error) {
      console.error('Error refining report:', error);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content:
          "Sorry, I couldn't refine the report at this moment. Please try again or contact support.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      const response = await fetch('/api/reports/regenerate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          documentId,
          reportId,
        }),
      });

      if (!response.ok) throw new Error('Failed to regenerate report');

      const data = await response.json();
      onReportUpdate(data.report || data.updatedReport);

      const regenerateMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Report regenerated from scratch based on the original analysis.',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, regenerateMessage]);
    } catch (error) {
      console.error('Error regenerating report:', error);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Failed to regenerate report. Please try again.',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-slate-50 to-white rounded-lg border border-slate-200 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white rounded-t-lg">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
          <h3 className="font-semibold text-slate-900">AI Report Refinement</h3>
        </div>
        <button
          onClick={handleRegenerate}
          disabled={isRegenerating || isLoadingReport}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Regenerate report from original analysis"
        >
          <RefreshCw
            size={16}
            className={isRegenerating ? 'animate-spin' : ''}
          />
          Regenerate
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-xs px-4 py-3 rounded-lg ${
                message.type === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-slate-100 text-slate-900 rounded-bl-none'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap leading-relaxed">
                {message.content}
              </p>
              <p
                className={`text-xs mt-2 ${
                  message.type === 'user'
                    ? 'text-blue-100'
                    : 'text-slate-500'
                }`}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 text-slate-900 rounded-lg rounded-bl-none px-4 py-3">
              <div className="flex items-center gap-2">
                <Loader size={16} className="animate-spin" />
                <p className="text-sm">Refining your report...</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-slate-200 bg-white rounded-b-lg">
        <form onSubmit={handleSendMessage} className="flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Suggest improvements (e.g., 'Make the defense strategy stronger')"
            disabled={isLoading || isRegenerating || isLoadingReport}
            className="flex-1 px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm disabled:bg-slate-50 disabled:text-slate-500"
          />
          <button
            type="submit"
            disabled={isLoading || isRegenerating || isLoadingReport || !input.trim()}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <Loader size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
