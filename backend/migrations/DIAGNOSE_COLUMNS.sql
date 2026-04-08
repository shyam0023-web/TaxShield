-- Quick diagnostic: Check if documents table has the right columns
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'documents' 
ORDER BY ordinal_position;
