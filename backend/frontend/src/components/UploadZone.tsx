'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadZoneProps {
  onFileUpload: (file: File) => void;
  isProcessing?: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onFileUpload, isProcessing = false }) => {
  const [dragActive, setDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0 && !isProcessing) {
      onFileUpload(acceptedFiles[0]);
    }
    setDragActive(false);
  }, [onFileUpload, isProcessing]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
      'text/*': ['.txt', '.csv']
    },
    multiple: false,
    disabled: isProcessing
  });

  return (
    <div
      {...getRootProps()}
      className={`
        relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
        transition-all duration-200 ease-in-out
        ${isDragActive || dragActive 
          ? 'border-blue-500 bg-blue-50' 
          : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
        }
        ${isProcessing 
          ? 'opacity-50 cursor-not-allowed border-gray-200 bg-gray-100' 
          : ''
        }
      `}
      onDragEnter={() => setDragActive(true)}
      onDragLeave={() => setDragActive(false)}
    >
      <input {...getInputProps()} />
      
      <div className="flex flex-col items-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        
        <div>
          <p className="text-lg font-medium text-gray-700">
            {isProcessing ? 'Processing...' : 'Drop your tax document here'}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {isProcessing 
              ? 'Please wait while we process your file'
              : 'or click to browse (PDF, images, or text files)'
            }
          </p>
        </div>
        
        {!isProcessing && (
          <div className="flex flex-wrap gap-2 justify-center">
            <span className="px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded">PDF</span>
            <span className="px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded">PNG</span>
            <span className="px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded">JPG</span>
            <span className="px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded">TXT</span>
            <span className="px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded">CSV</span>
          </div>
        )}
      </div>
    </div>
  );
};
