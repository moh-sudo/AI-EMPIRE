-- Fix a real bug found live 2026-08-09 while testing the flexible embeddings
-- system: memory_knowledge/memory_experience's embedding indexes used
-- ivfflat with `lists = 100`, an approximate-search index tuned for large
-- datasets. With only 1-2 real rows in the table, 100 clusters is wild
-- oversharding -- ivfflat's default single-probe search essentially never
-- lands on the right cluster unless the query vector is byte-identical to
-- a stored one (confirmed directly: self-match always found the row,
-- match_memory_knowledge/match_memory_experience with ANY genuinely
-- different-but-similar query vector consistently returned zero rows,
-- reproducibly, across 5 retries -- not a timing/replication issue).
--
-- Switching to HNSW: pgvector's modern recommended index type, performs
-- correctly at any dataset size without a "lists" parameter to mis-tune,
-- and doesn't need retraining/reindexing as the table grows the way
-- ivfflat does.

DROP INDEX IF EXISTS idx_memory_knowledge_embedding;
DROP INDEX IF EXISTS idx_memory_experience_embedding;

CREATE INDEX IF NOT EXISTS idx_memory_knowledge_embedding
  ON memory_knowledge USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_memory_experience_embedding
  ON memory_experience USING hnsw (embedding vector_cosine_ops);
