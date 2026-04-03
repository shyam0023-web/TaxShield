/**
 * TaxShield — Frontend Configuration
 * Central config for environment-dependent values.
 * 
 * In production (Vercel), set NEXT_PUBLIC_API_URL to your Railway backend URL.
 * Locally, it defaults to http://localhost:8000.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE_WITH_PREFIX = `${API_BASE}/api`;
