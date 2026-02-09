'use client';

import React, { useState, useEffect, useRef } from 'react';

interface DraftEditorProps {
  initialContent?: string;
  onSave?: (content: string) => void;
  readOnly?: boolean;
  placeholder?: string;
  autoSave?: boolean;
  autoSaveDelay?: number;
}

export const DraftEditor: React.FC<DraftEditorProps> = ({
  initialContent = '',
  onSave,
  readOnly = false,
  placeholder = 'Start typing your tax document analysis...',
  autoSave = true,
  autoSaveDelay = 2000
}) => {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setContent(initialContent);
  }, [initialContent]);

  useEffect(() => {
    if (autoSave && onSave && !readOnly) {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }

      autoSaveTimeoutRef.current = setTimeout(() => {
        handleSave();
      }, autoSaveDelay);
    }

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [content, autoSave, onSave, readOnly, autoSaveDelay]);

  const handleSave = async () => {
    if (!onSave || readOnly) return;

    setIsSaving(true);
    try {
      await onSave(content);
      setLastSaved(new Date());
    } catch (error) {
      console.error('Failed to save content:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.ctrlKey && e.key === 's' && !readOnly) {
      e.preventDefault();
      handleSave();
    }
  };

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
  const characterCount = content.length;

  return (
    <div className="relative w-full">
      {/* Header with status and actions */}
      <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-t-lg border border-gray-200">
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-600">
            <span className="font-medium">{wordCount}</span> words ·{' '}
            <span className="font-medium">{characterCount}</span> characters
          </div>
          
          {lastSaved && (
            <div className="text-sm text-gray-500">
              Last saved: {lastSaved.toLocaleTimeString()}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isSaving && (
            <div className="flex items-center gap-1 text-sm text-blue-600">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Saving...
            </div>
          )}
          
          {!readOnly && (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="relative">
        <textarea
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          readOnly={readOnly}
          placeholder={placeholder}
          className={`
            w-full min-h-[400px] p-4 border border-gray-200 rounded-b-lg
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            resize-y font-mono text-sm leading-relaxed
            ${readOnly ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}
          `}
          style={{ tabSize: 2 }}
        />
        
        {/* Auto-save indicator */}
        {autoSave && !readOnly && (
          <div className="absolute bottom-2 right-2 text-xs text-gray-400">
            Auto-save enabled • Ctrl+S to save
          </div>
        )}
      </div>

      {/* Empty state */}
      {!content && !readOnly && (
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
          <div className="text-center text-gray-400">
            <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
            <p className="text-sm">{placeholder}</p>
          </div>
        </div>
      )}
    </div>
  );
};
