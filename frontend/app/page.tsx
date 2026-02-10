import UploadNotice from "@/components/UploadNotice";
import ChatWidget from "@/components/ChatWidget";

export default function Home() {
  return (
    <div className="min-h-screen gradient-bg relative overflow-hidden">
      {/* Decorative Background Orbs */}
      <div className="floating-orb w-96 h-96 bg-indigo-600 top-0 left-1/4 opacity-30" />
      <div className="floating-orb w-80 h-80 bg-purple-600 bottom-0 right-1/4 opacity-20" style={{ animationDelay: '2s' }} />
      <div className="floating-orb w-64 h-64 bg-blue-600 top-1/2 right-0 opacity-20" style={{ animationDelay: '4s' }} />

      {/* Header */}
      <header className="relative z-10 py-12 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-4 py-2 mb-6">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-sm text-gray-400">Powered by LangGraph + Llama 3.3</span>
          </div>

          <h1 className="text-5xl md:text-6xl font-bold mb-4">
            <span className="gradient-text">TaxShield</span>
            <span className="text-white"> AI</span>
          </h1>

          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Automated GST Notice Response System with Multi-Agent RAG
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-6xl mx-auto px-4 pb-16">
        <UploadNotice />
      </main>

      {/* Footer */}
      <footer className="relative z-10 text-center py-8 border-t border-white/5">
        <div className="flex items-center justify-center gap-6 text-sm text-gray-500">
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            FAISS + BM25 Hybrid Search
          </span>
          <span className="w-1 h-1 bg-gray-600 rounded-full" />
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            Hallucination Audit
          </span>
          <span className="w-1 h-1 bg-gray-600 rounded-full" />
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Time-Bar Detection
          </span>
        </div>
      </footer>

      {/* Floating Chat Widget */}
      <ChatWidget />
    </div>
  );
}
