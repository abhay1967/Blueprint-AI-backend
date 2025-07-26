-- SQL to create the chats table in Supabase/Postgres
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_idea TEXT NOT NULL,
    response JSON NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
