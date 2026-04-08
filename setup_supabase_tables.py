"""
Script to set up Supabase tables for TaxShield
Requires: supabase-py, python-dotenv
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing Supabase credentials in .env")
    sys.exit(1)

# Initialize Supabase client
client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Create tables SQL
CREATE_TABLES_SQL = """
-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id text NOT NULL,
    report_type text NOT NULL,
    title text NOT NULL,
    content text,
    status text DEFAULT 'draft',
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);

-- Refinements table
CREATE TABLE IF NOT EXISTS refinements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id uuid REFERENCES reports(id) ON DELETE CASCADE,
    document_id text,
    user_suggestion text NOT NULL,
    refined_content text,
    explanation text,
    created_at timestamp DEFAULT now()
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name text NOT NULL,
    file_path text,
    notice_type text,
    extracted_data jsonb,
    created_at timestamp DEFAULT now()
);

-- Notices table
CREATE TABLE IF NOT EXISTS notices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    notice_type text,
    section text,
    issued_date date,
    response_due_date date,
    amount numeric,
    status text,
    created_at timestamp DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_reports_doc_id ON reports(document_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_refinements_report_id ON refinements(report_id);
CREATE INDEX IF NOT EXISTS idx_notices_type ON notices(notice_type);
"""

print("Creating Supabase tables...")
try:
    # Execute raw SQL via Supabase admin API
    # Note: This requires that you have SQL editor access or use Supabase dashboard
    print("⚠️  Tables must be created via Supabase dashboard SQL editor")
    print("\n🔗 Paste this SQL into your Supabase dashboard:")
    print("-" * 70)
    print(CREATE_TABLES_SQL)
    print("-" * 70)
    print("\n✅ After creating tables, restart the backend!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
