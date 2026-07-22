-- Phase 2 — Core Shared Services
-- Ref: CONTEXT.md "PHASE 2 — Core Shared Services"
-- Embedding dimension is 1536 (OpenAI text-embedding-3-small / ada-002),
-- since OPENAI_API_KEY is the designated embeddings provider in the stack.

-- ---------------------------------------------------------------------
-- memory_knowledge — facts/documents an agent has learned, embedded for
-- semantic recall
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_knowledge (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  division TEXT NOT NULL,
  agent_id TEXT,
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  source TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE memory_knowledge ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_memory_knowledge_embedding
  ON memory_knowledge USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memory_knowledge_division_agent
  ON memory_knowledge (division, agent_id);

-- ---------------------------------------------------------------------
-- memory_experience — episodic records of what an agent did and what
-- happened (e.g. Forex trade journal, per CONTEXT.md Phase 5)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_experience (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  division TEXT NOT NULL,
  agent_id TEXT,
  event_type TEXT NOT NULL,
  context TEXT NOT NULL,
  outcome TEXT,
  embedding VECTOR(1536),
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE memory_experience ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_memory_experience_embedding
  ON memory_experience USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memory_experience_division_agent
  ON memory_experience (division, agent_id);

-- ---------------------------------------------------------------------
-- memory_identity — stable per-agent identity facts (key/value), rarely
-- written, frequently read at agent startup
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_identity (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT NOT NULL,
  division TEXT NOT NULL,
  key TEXT NOT NULL,
  value JSONB NOT NULL,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (agent_id, key)
);
ALTER TABLE memory_identity ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------
-- model_registry — every model the Hybrid Router is allowed to route to
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_registry (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  model_identifier TEXT UNIQUE NOT NULL,
  provider TEXT NOT NULL CHECK (provider IN ('local', 'anthropic', 'openai')),
  model_class TEXT NOT NULL CHECK (model_class IN ('A','B','C','D')),
  context_window INTEGER,
  cost_per_1k_input_usd NUMERIC(10,6) DEFAULT 0,
  cost_per_1k_output_usd NUMERIC(10,6) DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deprecated','disabled')),
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE model_registry ENABLE ROW LEVEL SECURITY;

INSERT INTO model_registry (model_identifier, provider, model_class, context_window, status)
VALUES
  ('ollama/llama3-8b', 'local', 'B', 8192, 'active'),
  ('claude-sonnet-5', 'anthropic', 'A', 200000, 'active')
ON CONFLICT (model_identifier) DO NOTHING;

-- ---------------------------------------------------------------------
-- prompt_registry — every versioned prompt module, with a hash of its
-- Immutable Core (Boundaries) section so tampering can be detected at
-- load time. Naming convention: {division}_{agent}_{version}.json,
-- stored under shared/prompts/.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prompt_registry (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT NOT NULL,
  division TEXT NOT NULL,
  version TEXT NOT NULL,
  file_path TEXT NOT NULL,
  boundaries_hash TEXT NOT NULL,
  approved_by TEXT,
  approved_date TIMESTAMPTZ,
  active BOOLEAN NOT NULL DEFAULT true,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (agent_id, version)
);
ALTER TABLE prompt_registry ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------
-- Vector similarity search RPCs. supabase-py's REST client can't express
-- pgvector's `<->` distance operator directly, so semantic search goes
-- through these SECURITY DEFINER functions via client.rpc(...).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_memory_knowledge(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 5,
  filter_division TEXT DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  division TEXT,
  agent_id TEXT,
  content TEXT,
  source TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT
    id, division, agent_id, content, source, metadata,
    1 - (embedding <=> query_embedding) AS similarity
  FROM memory_knowledge
  WHERE embedding IS NOT NULL
    AND (filter_division IS NULL OR division = filter_division)
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

CREATE OR REPLACE FUNCTION match_memory_experience(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 5,
  filter_division TEXT DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  division TEXT,
  agent_id TEXT,
  event_type TEXT,
  context TEXT,
  outcome TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT
    id, division, agent_id, event_type, context, outcome, metadata,
    1 - (embedding <=> query_embedding) AS similarity
  FROM memory_experience
  WHERE embedding IS NOT NULL
    AND (filter_division IS NULL OR division = filter_division)
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Note on RLS: all Phase 2 tables have RLS enabled with no policies, so
-- anon/authenticated get zero access by default; only the service_role
-- key (used by backend Python modules) bypasses RLS, consistent with
-- Phase 1's circuit_breakers/job_queue/platform_settings. The two
-- SECURITY DEFINER functions above run as the function owner (bypassing
-- RLS internally) but are only reachable by callers holding the
-- service_role key via PostgREST's rpc endpoint, so this does not open
-- anon/authenticated access.
