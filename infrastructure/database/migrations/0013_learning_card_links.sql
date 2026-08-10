-- Knowledge-linked prompts -- one of the real concepts worth taking from
-- Orbit even without adopting Orbit itself (Mohamed's explicit call,
-- 2026-08-09): a card can reference other cards it's conceptually related
-- to, mirroring the same idea Obsidian uses for notes (bidirectional
-- links). A join table, not an array column, so both directions are
-- queryable without keeping two array columns in sync by hand.
--
-- Deliberately its own table rather than a change to learning_cards --
-- the SM-2 scheduling columns on learning_cards stay exactly as they are;
-- linking is an orthogonal concept layered on top, owned by the engine
-- abstraction (agents/learning/engine.py), not the SM-2 algorithm itself.

CREATE TABLE IF NOT EXISTS learning_card_links (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  card_id UUID NOT NULL REFERENCES learning_cards(id) ON DELETE CASCADE,
  related_card_id UUID NOT NULL REFERENCES learning_cards(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CHECK (card_id <> related_card_id),
  UNIQUE (card_id, related_card_id)
);
ALTER TABLE learning_card_links ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_learning_card_links_card ON learning_card_links(card_id);
CREATE INDEX IF NOT EXISTS idx_learning_card_links_related ON learning_card_links(related_card_id);
