-- FIXERA CONNECTOR — REFERENCE ONLY, NOT CURRENTLY ACTIVE
--
-- This SQL runs against FIXERA'S Supabase project (ref igncnngkbmswomphbhwa),
-- NOT AI_EMPIRE's own database. It does not belong in
-- infrastructure/database/migrations/ (which is exclusively for AI_EMPIRE's
-- own Supabase project) — kept here separately for that reason.
--
-- STATUS (2026-07-23): Created and then reverted the same day. The 5 views
-- and the ai_empire_reader role were successfully created in Fixera's
-- database, but the connector could not be proven to work: password
-- authentication consistently failed via Supabase's pooler (Supavisor) for
-- every reasonable configuration tried (fresh role, exact known password,
-- both session/transaction pooler modes, after waiting out the documented
-- circuit-breaker cooldown). Direct (non-pooled) connection was not testable
-- from this machine's network, which has no functional IPv6 connectivity.
-- This may be a genuine Supavisor limitation with custom roles — see
-- CONTEXT.md Session Log, 2026-07-23, for full troubleshooting detail.
-- Everything below was reverted (REVOKE + DROP ROLE + DROP VIEW) before
-- this file was written, so Fixera's database currently has none of this.
--
-- To retry: run the block below in Fixera's SQL Editor (FIXERA-SERVICES
-- project, not AI_EMPIRE's), replacing the password placeholder, then set
-- FIXERA_DB_HOST/PORT/NAME/USER/PASSWORD in moh-sudo's .env per the format
-- documented in CONTEXT.md.
--
-- Column choices below deliberately exclude PII/sensitive fields per Law 6
-- (only access what's needed): OTPs, raw addresses/notes, phone numbers,
-- mpesa transaction references, national ID numbers, photos, and all
-- free-text personal statement/comment fields. See CONTEXT.md's "Fixera
-- Relationship" section for the full reasoning.

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

-- Replace with a password you choose yourself.
CREATE ROLE ai_empire_reader WITH LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';

GRANT USAGE ON SCHEMA public TO ai_empire_reader;
GRANT SELECT ON
  ai_empire_bookings_summary,
  ai_empire_payments_summary,
  ai_empire_disputes_summary,
  ai_empire_reviews_summary,
  ai_empire_workers_summary
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
