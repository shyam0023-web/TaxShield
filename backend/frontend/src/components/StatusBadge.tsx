'use client';

import React from 'react';

export type StatusType = 'idle' | 'processing' | 'success' | 'error';

interface StatusBadgeProps {
  status: StatusType;
  message?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, message }) => {
  const getStatusConfig = (status: StatusType) => {
    switch (status) {
      case 'processing':
        return {
          bgColor: 'bg-blue-100',
          textColor: 'text-blue-800',
          borderColor: 'border-blue-200',
          icon: (
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
          ),
          defaultText: 'Processing...'
        };
      case 'success':
        return {
          bgColor: 'bg-green-100',
          textColor: 'text-green-800',
          borderColor: 'border-green-200',
          icon: (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          ),
          defaultText: 'Success'
        };
      case 'error':
        return {
          bgColor: 'bg-red-100',
          textColor: 'text-red-800',
          borderColor: 'border-red-200',
          icon: (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          ),
          defaultText: 'Error'
        };
      case 'idle':
      default:
        return {
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-800',
          borderColor: 'border-gray-200',
          icon: null,
          defaultText: 'Ready'
        };
    }
  };

  const config = getStatusConfig(status);
  const displayText = message || config.defaultText;

  if (status === 'idle') {
    return null;
  }

  return (
    <div className={`
      inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium
      border ${config.bgColor} ${config.textColor} ${config.borderColor}
    `}>
      {config.icon}
      <span>{displayText}</span>
    </div>
  );
};
