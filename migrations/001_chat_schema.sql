-- Chat Interface Database Schema Migration
-- Execute this in Supabase SQL Editor or via migrations

-- Create chat_sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours') NOT NULL,
    model_preference TEXT DEFAULT 'llama3.2' NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Optional: Link to invoice context for better integration
    current_invoice_id TEXT,
    
    -- Audit fields
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create chat_messages table  
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE NOT NULL,
    role TEXT CHECK (role IN ('user', 'assistant', 'system', 'tool')) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb, -- Store tool_calls, confidence, processing_time, etc.
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Create session_files table for uploaded files
CREATE TABLE IF NOT EXISTS session_files (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type TEXT,
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processed', 'failed')),
    uploaded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Ensure unique file paths
    UNIQUE(file_path)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_expires_at ON chat_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_invoice_id ON chat_sessions(current_invoice_id);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);

CREATE INDEX IF NOT EXISTS idx_session_files_session_id ON session_files(session_id);
CREATE INDEX IF NOT EXISTS idx_session_files_uploaded_at ON session_files(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_session_files_status ON session_files(processing_status);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at on chat_sessions
CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function for automatic session cleanup (optional - run as scheduled job)
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired sessions (cascades to messages and files)
    DELETE FROM chat_sessions 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Enable Row Level Security (RLS) for multi-tenant support if needed in future
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;  
ALTER TABLE session_files ENABLE ROW LEVEL SECURITY;

-- Create default policies (allow all for now, customize later if needed)
CREATE POLICY "Enable all access for chat_sessions" ON chat_sessions
    FOR ALL USING (true);

CREATE POLICY "Enable all access for chat_messages" ON chat_messages
    FOR ALL USING (true);

CREATE POLICY "Enable all access for session_files" ON session_files
    FOR ALL USING (true);

-- Grant necessary permissions (adjust role as needed)
GRANT ALL ON chat_sessions TO authenticated, anon;
GRANT ALL ON chat_messages TO authenticated, anon;
GRANT ALL ON session_files TO authenticated, anon;

GRANT USAGE ON SCHEMA public TO authenticated, anon;

-- Add helpful comments
COMMENT ON TABLE chat_sessions IS 'Chat sessions with configurable expiration and model preferences';
COMMENT ON TABLE chat_messages IS 'Chat messages with role-based structure and metadata for tool calls';  
COMMENT ON TABLE session_files IS 'Uploaded files tied to chat sessions with processing status tracking';

COMMENT ON COLUMN chat_sessions.current_invoice_id IS 'Optional reference to invoiceline.invoiceid for context';
COMMENT ON COLUMN chat_messages.metadata IS 'JSON metadata including tool_calls, confidence, processing_time, etc';
COMMENT ON COLUMN session_files.processing_status IS 'Track file processing: pending, processed, failed';