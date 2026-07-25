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

-- Added 2026-07-24: Partner Verification support. Unlike the 6 views
-- above (which just exclude sensitive columns), workers.service_details
-- is a JSONB blob whose *shape* varies by partner_role and legitimately
-- contains sensitive leaf values (national ID numbers, KYC/ID photo
-- URLs, crew/reference names and phone numbers, insurance policy
-- numbers). Rather than excluding it entirely (which would leave the
-- Partner Verification agent blind to what's actually missing from an
-- application), this recursively redacts every string leaf to a
-- presence boolean, so the agent can check "is this required field
-- filled in" without ever seeing the value itself.
--
-- Two date semantics, disambiguated by key suffix (matches the field
-- names OnboardingPage.jsx already writes): keys ending in "ExpiryDate"
-- (e.g. insurance coverage) redact to "is this date still in the
-- future" (not yet expired); other keys ending in "Date" (e.g.
-- *BgCheckDate) redact to "is this date within the last 6 months"
-- (recently issued). Any other string redacts to plain presence.
CREATE OR REPLACE FUNCTION ai_empire_redact_to_presence(data jsonb)
RETURNS jsonb
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  result jsonb;
  key text;
  val jsonb;
  arr_result jsonb;
  item jsonb;
BEGIN
  IF data IS NULL THEN
    RETURN NULL;
  END IF;

  CASE jsonb_typeof(data)
    WHEN 'object' THEN
      result := '{}'::jsonb;
      FOR key, val IN SELECT * FROM jsonb_each(data) LOOP
        IF key ILIKE '%ExpiryDate' AND jsonb_typeof(val) = 'string' THEN
          BEGIN
            result := result || jsonb_build_object(
              key, to_jsonb((val #>> '{}')::date > current_date)
            );
          EXCEPTION WHEN OTHERS THEN
            result := result || jsonb_build_object(key, ai_empire_redact_to_presence(val));
          END;
        ELSIF key ILIKE '%Date' AND jsonb_typeof(val) = 'string' THEN
          BEGIN
            result := result || jsonb_build_object(
              key, to_jsonb((val #>> '{}')::date > (current_date - interval '6 months'))
            );
          EXCEPTION WHEN OTHERS THEN
            result := result || jsonb_build_object(key, ai_empire_redact_to_presence(val));
          END;
        ELSE
          result := result || jsonb_build_object(key, ai_empire_redact_to_presence(val));
        END IF;
      END LOOP;
      RETURN result;
    WHEN 'array' THEN
      arr_result := '[]'::jsonb;
      FOR item IN SELECT * FROM jsonb_array_elements(data) LOOP
        arr_result := arr_result || jsonb_build_array(ai_empire_redact_to_presence(item));
      END LOOP;
      RETURN arr_result;
    WHEN 'string' THEN
      RETURN to_jsonb((data #>> '{}') IS NOT NULL AND (data #>> '{}') <> '');
    ELSE
      RETURN data; -- booleans/numbers pass through unchanged
  END CASE;
END;
$$;

CREATE OR REPLACE VIEW ai_empire_partner_verification_summary AS
SELECT
  id,
  partner_role,
  verification_status,
  onboarding_complete,
  created_at,
  (profile_photo_url IS NOT NULL AND profile_photo_url <> '') AS has_profile_photo,
  (id_photo_url      IS NOT NULL AND id_photo_url      <> '') AS has_id_photo,
  (tax_pin           IS NOT NULL AND tax_pin           <> '') AS has_tax_pin,
  ai_empire_redact_to_presence(service_details) AS service_details_presence
FROM workers
WHERE onboarding_complete = true
  AND deleted_at IS NULL;

-- Added 2026-07-24: Platform Governance support. Exposes only schema
-- *structure* (table/column/trigger/view names, column data types) via
-- information_schema -- never any row data. This is what lets Platform
-- Governance check documented schema claims (like the trg_wallet_gate
-- gap noted below) against what's actually live, instead of staying
-- permanently mock-based.
CREATE OR REPLACE VIEW ai_empire_schema_columns_summary AS
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public';

CREATE OR REPLACE VIEW ai_empire_schema_triggers_summary AS
SELECT event_object_table AS table_name, trigger_name
FROM information_schema.triggers
WHERE trigger_schema = 'public';

CREATE OR REPLACE VIEW ai_empire_schema_views_summary AS
SELECT table_name AS view_name
FROM information_schema.views
WHERE table_schema = 'public';

-- Replace with a password you choose yourself.
CREATE ROLE ai_empire_reader WITH LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';

GRANT USAGE ON SCHEMA public TO ai_empire_reader;
GRANT SELECT ON
  ai_empire_bookings_summary,
  ai_empire_payments_summary,
  ai_empire_disputes_summary,
  ai_empire_reviews_summary,
  ai_empire_workers_summary,
  ai_empire_tickets_summary,
  ai_empire_partner_verification_summary,
  ai_empire_schema_columns_summary,
  ai_empire_schema_triggers_summary,
  ai_empire_schema_views_summary
TO ai_empire_reader;

-- Also discovered along the way, worth knowing about independent of this
-- connector: Fixera's `trg_wallet_gate` trigger and `can_receive_jobs`
-- column (referenced in this file's own governance notes and in the
-- enforce_wallet_minimum.sql migration) do NOT actually exist in
-- production -- confirmed via information_schema.triggers and
-- information_schema.columns. The wallet-minimum enforcement Fixera's own
-- docs assume is live is not currently active. This is Fixera's own
-- codebase/ops issue to fix, not something touched from here. As of
-- 2026-07-24 this is also the first real drift case Platform Governance's
-- run_governance_sweep() checks for automatically.

-- Also not found in production despite being referenced in a migration
-- file: the `partner_wallet_status` view. Only `partner_ratings` exists.
