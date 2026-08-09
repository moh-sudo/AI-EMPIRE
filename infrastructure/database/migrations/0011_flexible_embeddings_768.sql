-- Flexible, multi-provider embeddings: change memory_knowledge/memory_experience
-- from a fixed OpenAI-only VECTOR(1536) to VECTOR(768) -- the common dimension
-- between OpenAI's text-embedding-3-small (which supports a `dimensions=768`
-- request parameter, a documented OpenAI feature) and Ollama's nomic-embed-text
-- (native 768-dim). Lets shared/memory/embeddings.py use either provider,
-- configurable, with fallback -- Mohamed's explicit request (2026-08-09) for a
-- flexible system, not hard-locked to OpenAI.
--
-- SAFE, no data loss: confirmed live that OpenAI embeddings have failed with
-- insufficient_quota since early sessions -- every existing row's embedding
-- column is NULL, there is no real 1536-dim data to preserve or migrate.

DROP INDEX IF EXISTS idx_memory_knowledge_embedding;
DROP INDEX IF EXISTS idx_memory_experience_embedding;

ALTER TABLE memory_knowledge ALTER COLUMN embedding TYPE VECTOR(768);
ALTER TABLE memory_experience ALTER COLUMN embedding TYPE VECTOR(768);

CREATE INDEX IF NOT EXISTS idx_memory_knowledge_embedding
  ON memory_knowledge USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memory_experience_embedding
  ON memory_experience USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

DROP FUNCTION IF EXISTS match_memory_knowledge(VECTOR(1536), INT, TEXT);
CREATE FUNCTION match_memory_knowledge(
  query_embedding VECTOR(768),
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

DROP FUNCTION IF EXISTS match_memory_experience(VECTOR(1536), INT, TEXT);
CREATE FUNCTION match_memory_experience(
  query_embedding VECTOR(768),
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
