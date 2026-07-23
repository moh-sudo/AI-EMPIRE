-- FIXERA CONNECTOR — REFERENCE / SETUP SQL
--
-- This SQL runs against FIXERA'S Supabase project (ref igncnngkbmswomphbhwa),
-- NOT AI_EMPIRE's own database. It does not belong in
-- infrastructure/database/migrations/ (which is exclusively for AI_EMPIRE's
-- own Supabase project) — kept here separately for that reason.
--
-- STATUS (2026-07-23): LIVE AND WORKING. Verified: connects as
-- ai_empire_reader, reads real data from all 6 views, write access is
-- correctly blocked (InsufficientPrivilege), and access to raw tables
-- outside these 6 views is also correctly blocked. An earlier same-day
-- attempt hit persistent "password authentication failed" errors despite
-- correct credentials — root cause understood as Supavisor (Fixera's
-- Supabase pooler) running multiple backend nodes that don't all cache a
-- newly-created role's credentials simultaneously; a connection landing on
-- a node that hasn't caught up fails even with correct credentials. Fixed
-- with retry logic in shared/fixera_connector.py (not by changing anything
-- here). See CONTEXT.md Session Log, 2026-07-23, for full detail.
--
-- To recreate from scratch (e.g. after a revert): run the whole block below
-- in Fixera's SQL Editor (FIXERA-SERVICES project, not AI_EMPIRE's),
-- choosing your own password, then set FIXERA_DB_HOST/PORT/NAME/USER/
-- PASSWORD in moh-sudo's .env per the format documented in CONTEXT.md.
--
-- Column choices below deliberately exclude PII/sensitive fields per Law 6
-- (only access what's needed): OTPs, raw addresses/notes, phone numbers,
-- mpesa transaction references, national ID numbers, photos, and all
-- free-text personal statement/message/comment fields. See CONTEXT.md's
-- "Fixera Relationship" section for the full reasoning.

CREATE OR REPLACE VIEW ai_empire_bookings_summary AS
SELECT
  id, user_id AS customer_id, worker_id, worker_name, service, service_name,
  category, sub_service, service_mode, status,
  price, commission_rate, commission_amount, professional_earning,
  service_area_id, fulfillment_stage,
  cancellation_reason, cancellation_fee,
  scheduled_date, scheduled_time, booking_date, booking_time,
  confirmed_at, arrived_at, departed_at, delivered_at, completed_at,
  received_at, prep_started_at, ready_at, accepted_at,
  assigned_rider_id, carrier_user_id, rider_name, rider_vehicle,
  timeout_count, last_timed_out_worker,
  created_at, updated_at
FROM bookings;

CREATE OR REPLACE VIEW ai_empire_payments_summary AS
SELECT
  id, customer_id, payee_id, payee_role, ref_type, ref_id, purpose,
  amount, commission_rate, commission_amount, partner_amount, method,
  status, settlement_status, paid_at, created_at
FROM payments;

CREATE OR REPLACE VIEW ai_empire_disputes_summary AS
SELECT
  id, booking_id, booking_ref, service, booking_date, customer_id,
  partner_id, partner_role, status, ruling, compensation_action,
  customer_submitted_at, partner_submitted_at, sla_escalated_at,
  resolved_at, created_at, updated_at
FROM disputes;

CREATE OR REPLACE VIEW ai_empire_reviews_summary AS
SELECT
  id, booking_id, worker_id, customer_id, order_id, order_type,
  reviewer_id, reviewee_id, reviewee_type,
  rating, quality, punctuality, professionalism, tags,
  status, created_at
FROM reviews;

CREATE OR REPLACE VIEW ai_empire_workers_summary AS
SELECT
  id, full_name, partner_role, service, business_name, business_type,
  vehicle_type, product_category, service_area, city,
  status, is_available, is_open, onboarding_complete, verification_status,
  rating, total_jobs, earnings, wallet_balance,
  years_in_operation,
  created_at
FROM workers
WHERE deleted_at IS NULL;

-- Added 2026-07-23 (after the initial 5): general support tickets, used by
-- Customer Support (user_type='customer') and Partner Support
-- (user_type='partner') agents. Excludes subject/message (free-text
-- personal content), admin_note (internal), and user_name/user_email
-- (PII). refund_decision IS included: reading an already-made decision to
-- communicate status is these agents' job, distinct from authorizing one.
-- Fixera also has moving_support_tickets (movers-module-specific) and
-- ticket_notes, not covered here -- out of scope unless a real need shows up.
CREATE OR REPLACE VIEW ai_empire_tickets_summary AS
SELECT
  id, user_id, user_type, category, status, department, priority,
  created_at, updated_at, resolved_at, refund_decision,
  assigned_to, assigned_name, sla_deadline, sla_escalated_at
FROM support_tickets;

-- Replace with a password you choose yourself.
CREATE ROLE ai_empire_reader WITH LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';

GRANT USAGE ON SCHEMA public TO ai_empire_reader;
GRANT SELECT ON
  ai_empire_bookings_summary,
  ai_empire_payments_summary,
  ai_empire_disputes_summary,
  ai_empire_reviews_summary,
  ai_empire_workers_summary,
  ai_empire_tickets_summary
TO ai_empire_reader;

-- Also discovered along the way, worth knowing about independent of this
-- connector: Fixera's `trg_wallet_gate` trigger and `can_receive_jobs`
-- column (referenced in this file's own governance notes and in the
-- enforce_wallet_minimum.sql migration) do NOT actually exist in
-- production -- confirmed via information_schema.triggers and
-- information_schema.columns. The wallet-minimum enforcement Fixera's own
-- docs assume is live is not currently active. This is Fixera's own
-- codebase/ops issue to fix, not something touched from here.

-- Also not found in production despite being referenced in a migration
-- file: the `partner_wallet_status` view. Only `partner_ratings` exists.
