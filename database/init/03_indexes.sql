-- Full-text search indexes for Arabic content
CREATE INDEX IF NOT EXISTS idx_laws_full_text_tsv ON laws USING GIN (to_tsvector('arabic', COALESCE(full_text, '')));
CREATE INDEX IF NOT EXISTS idx_laws_title_tsv ON laws USING GIN (to_tsvector('arabic', COALESCE(title, '')));
CREATE INDEX IF NOT EXISTS idx_rulings_full_text_tsv ON rulings USING GIN (to_tsvector('arabic', COALESCE(full_text, '')));
CREATE INDEX IF NOT EXISTS idx_documents_content_tsv ON documents USING GIN (to_tsvector('arabic', COALESCE(content, '')));

-- Partial indexes for active laws
CREATE INDEX IF NOT EXISTS idx_laws_active ON laws (is_active) WHERE is_active = true;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_laws_year ON laws (year);
CREATE INDEX IF NOT EXISTS idx_laws_category ON laws (category);
CREATE INDEX IF NOT EXISTS idx_laws_law_number ON laws (law_number);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments (user_id);
CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents (case_id);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents (uploaded_by);
