--
-- PostgreSQL database dump
--

\restrict nzeaIJM9lJaLCc7PZ55wX3AxaNPzikwmchUSNFB6uXH2m9beo5UtcKD2zgFzWJo

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: analytics; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA analytics;


ALTER SCHEMA analytics OWNER TO postgres;

--
-- Name: etl; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA etl;


ALTER SCHEMA etl OWNER TO postgres;

--
-- Name: events; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA events;


ALTER SCHEMA events OWNER TO postgres;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: fn_append_price_history(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_append_price_history() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Only append if price changed or it's a new day
    IF NOT EXISTS (
        SELECT 1 FROM price_history
        WHERE product_id = NEW.product_id
          AND store      = NEW.store
          AND price_date = NEW.price_date
    ) THEN
        INSERT INTO price_history (
            product_id, gtin, store,
            price_chf, price_per_100g,
            is_promotion, discount_pct,
            price_date
        ) VALUES (
            NEW.product_id, NEW.gtin, NEW.store,
            NEW.price_chf, NEW.price_per_100g,
            NEW.is_promotion, NEW.discount_pct,
            NEW.price_date
        );
    END IF;
    RETURN NEW;
END; $$;


ALTER FUNCTION public.fn_append_price_history() OWNER TO postgres;

--
-- Name: fn_clear_nutrition_cache(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_clear_nutrition_cache() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE products
    SET nutrition_cache = NULL,
        updated_at = NOW()
    WHERE id = OLD.product_id;
    RETURN OLD;
END; $$;


ALTER FUNCTION public.fn_clear_nutrition_cache() OWNER TO postgres;

--
-- Name: fn_compute_unit_prices(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_compute_unit_prices() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    qty_in_base NUMERIC;
BEGIN
    -- price_per_100g: normalise everything to per-100g or per-100ml
    IF NEW.unit_quantity IS NOT NULL AND NEW.unit_quantity > 0
       AND NEW.unit_type IN ('g', 'ml', 'kg', 'l', 'cl')
    THEN
        qty_in_base := CASE NEW.unit_type
            WHEN 'kg' THEN NEW.unit_quantity * 1000
            WHEN 'l'  THEN NEW.unit_quantity * 1000
            WHEN 'cl' THEN NEW.unit_quantity * 10
            ELSE NEW.unit_quantity
        END;
        NEW.price_per_100g := ROUND(
            NEW.price_chf / qty_in_base * 100, 4
        );
    END IF;

    -- price_per_pack_unit
    IF NEW.units_per_pack IS NOT NULL AND NEW.units_per_pack > 0 THEN
        NEW.price_per_pack_unit := ROUND(
            NEW.price_chf / NEW.units_per_pack, 4
        );
    END IF;

    -- discount_pct
    IF NEW.is_promotion
       AND NEW.original_price_chf IS NOT NULL
       AND NEW.original_price_chf > 0
    THEN
        NEW.discount_pct := ROUND(
            (NEW.original_price_chf - NEW.price_chf)
            / NEW.original_price_chf * 100, 2
        );
    END IF;

    RETURN NEW;
END; $$;


ALTER FUNCTION public.fn_compute_unit_prices() OWNER TO postgres;

--
-- Name: fn_iso_week(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_iso_week(d date) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT EXTRACT(WEEK FROM d)::INTEGER;
$$;


ALTER FUNCTION public.fn_iso_week(d date) OWNER TO postgres;

--
-- Name: fn_rebuild_price_snapshot(character varying, date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_rebuild_price_snapshot(p_gtin character varying, p_date date DEFAULT CURRENT_DATE) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    prices_obj      JSONB := '{}';
    per100_obj      JSONB := '{}';
    min_price       NUMERIC := NULL;
    max_price       NUMERIC := NULL;
    min_store       TEXT;
    max_store       TEXT;
    store_count     INTEGER := 0;
    rec             RECORD;
BEGIN
    FOR rec IN
        SELECT pp.store, pp.price_chf, pp.price_per_100g
        FROM product_prices pp
        JOIN products p ON p.id = pp.product_id
        WHERE p.gtin = p_gtin
          AND pp.price_date = p_date
          AND pp.price_chf IS NOT NULL
    LOOP
        prices_obj := prices_obj || jsonb_build_object(
            rec.store, rec.price_chf
        );
        IF rec.price_per_100g IS NOT NULL THEN
            per100_obj := per100_obj || jsonb_build_object(
                rec.store, rec.price_per_100g
            );
        END IF;
        store_count := store_count + 1;
        IF min_price IS NULL OR rec.price_chf < min_price THEN
            min_price := rec.price_chf; min_store := rec.store;
        END IF;
        IF max_price IS NULL OR rec.price_chf > max_price THEN
            max_price := rec.price_chf; max_store := rec.store;
        END IF;
    END LOOP;

    IF store_count > 0 THEN
        INSERT INTO store_price_snapshot (
            gtin, snapshot_date,
            prices_chf, prices_per_100g,
            cheapest_store, cheapest_price,
            most_expensive_store, most_expensive_price,
            price_spread_chf, price_spread_pct,
            stores_compared
        ) VALUES (
            p_gtin, p_date,
            prices_obj, per100_obj,
            min_store, min_price,
            max_store, max_price,
            ROUND(max_price - min_price, 2),
            ROUND((max_price - min_price) / NULLIF(min_price, 0) * 100, 2),
            store_count
        )
        ON CONFLICT (gtin, snapshot_date) DO UPDATE SET
            prices_chf           = EXCLUDED.prices_chf,
            prices_per_100g      = EXCLUDED.prices_per_100g,
            cheapest_store       = EXCLUDED.cheapest_store,
            cheapest_price       = EXCLUDED.cheapest_price,
            most_expensive_store = EXCLUDED.most_expensive_store,
            most_expensive_price = EXCLUDED.most_expensive_price,
            price_spread_chf     = EXCLUDED.price_spread_chf,
            price_spread_pct     = EXCLUDED.price_spread_pct,
            stores_compared      = EXCLUDED.stores_compared,
            updated_at           = NOW();
    END IF;
END; $$;


ALTER FUNCTION public.fn_rebuild_price_snapshot(p_gtin character varying, p_date date) OWNER TO postgres;

--
-- Name: fn_rebuild_unified_master(uuid); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_rebuild_unified_master(p_unified_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_master UUID;
BEGIN
    SELECT product_id INTO v_master
    FROM unified_product_members
    WHERE unified_id = p_unified_id
      AND is_master  = true
    LIMIT 1;

    UPDATE unified_products
    SET master_product_id = v_master,
        updated_at        = NOW()
    WHERE unified_id = p_unified_id;
END;
$$;


ALTER FUNCTION public.fn_rebuild_unified_master(p_unified_id uuid) OWNER TO postgres;

--
-- Name: fn_set_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;


ALTER FUNCTION public.fn_set_updated_at() OWNER TO postgres;

--
-- Name: fn_sync_nutrition_cache(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_sync_nutrition_cache() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE products
    SET nutrition_cache = jsonb_build_object(
        'energy_kcal_100',  NEW.energy_kcal_100,
        'fat_100',          NEW.fat_100,
        'carbs_100',        NEW.carbs_100,
        'sugars_100',       NEW.sugars_100,
        'protein_100',      NEW.protein_100,
        'salt_100',         NEW.salt_100,
        'nutri_score',      NEW.nutri_score,
        'nova_group',       NEW.nova_group,
        'serving_size_g',   NEW.serving_size_g
    ),
    updated_at = NOW()
    WHERE id = NEW.product_id;
    RETURN NEW;
END; $$;


ALTER FUNCTION public.fn_sync_nutrition_cache() OWNER TO postgres;

--
-- Name: fn_sync_unified_master(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_sync_unified_master() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.is_master = true THEN
        UPDATE unified_products
        SET master_product_id = NEW.product_id,
            updated_at = NOW()
        WHERE unified_id = NEW.unified_id;
    END IF;
    RETURN NEW;
END; $$;


ALTER FUNCTION public.fn_sync_unified_master() OWNER TO postgres;

--
-- Name: fn_validate_price_product_ref(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_validate_price_product_ref() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    ref RECORD;
BEGIN
    SELECT gtin, store INTO ref
    FROM products WHERE id = NEW.product_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'product_id % not found in products', NEW.product_id;
    END IF;

    -- Auto-correct denormalized fields from master
    NEW.gtin  := ref.gtin;
    NEW.store := ref.store;

    RETURN NEW;
END; $$;


ALTER FUNCTION public.fn_validate_price_product_ref() OWNER TO postgres;

--
-- Name: rls_auto_enable(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rls_auto_enable() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$$;


ALTER FUNCTION public.rls_auto_enable() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: allergen_risk; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.allergen_risk (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    allergen_type text NOT NULL,
    year integer NOT NULL,
    month_number integer NOT NULL,
    alert_count integer DEFAULT 0,
    unique_users integer DEFAULT 0,
    products_affected integer DEFAULT 0,
    stores_affected integer DEFAULT 0,
    contains_count integer DEFAULT 0,
    may_contain_count integer DEFAULT 0,
    conflict_count integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.allergen_risk OWNER TO postgres;

--
-- Name: api_usage; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.api_usage (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    year integer NOT NULL,
    week_number integer NOT NULL,
    endpoint text NOT NULL,
    total_requests integer DEFAULT 0,
    success_count integer DEFAULT 0,
    error_count integer DEFAULT 0,
    avg_response_ms integer,
    p95_response_ms integer,
    unique_clients integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.api_usage OWNER TO postgres;

--
-- Name: app_behaviour; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.app_behaviour (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    year integer NOT NULL,
    week_number integer NOT NULL,
    platform text,
    lang character(2),
    scan_sessions integer DEFAULT 0,
    search_sessions integer DEFAULT 0,
    chat_sessions integer DEFAULT 0,
    total_scans integer DEFAULT 0,
    total_searches integer DEFAULT 0,
    total_chats integer DEFAULT 0,
    zero_result_searches integer DEFAULT 0,
    scan_to_save_rate numeric(5,2),
    search_to_save_rate numeric(5,2),
    chat_to_save_rate numeric(5,2),
    chat_follow_up_rate numeric(5,2),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.app_behaviour OWNER TO postgres;

--
-- Name: b2b_report_access; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.b2b_report_access (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    client_name text NOT NULL,
    client_type text,
    report_type text NOT NULL,
    date_range_start date,
    date_range_end date,
    records_accessed integer,
    is_anonymised boolean DEFAULT true,
    api_key_hash text,
    accessed_at timestamp with time zone DEFAULT now(),
    CONSTRAINT b2b_report_access_client_type_check CHECK ((client_type = ANY (ARRAY['retailer'::text, 'food_brand'::text, 'health_insurer'::text, 'academic'::text, 'government'::text, 'other'::text])))
);


ALTER TABLE analytics.b2b_report_access OWNER TO postgres;

--
-- Name: category_analytics; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.category_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    category text NOT NULL,
    store text,
    lang character(2),
    year integer NOT NULL,
    month_number integer NOT NULL,
    scan_count integer DEFAULT 0,
    search_count integer DEFAULT 0,
    save_count integer DEFAULT 0,
    avg_price_chf numeric(10,2),
    top_verdict text,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.category_analytics OWNER TO postgres;

--
-- Name: dietary_trends; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.dietary_trends (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dietary_type text NOT NULL,
    region text,
    lang character(2),
    year integer NOT NULL,
    month_number integer NOT NULL,
    user_count integer DEFAULT 0,
    scan_count integer DEFAULT 0,
    search_count integer DEFAULT 0,
    growth_pct numeric(5,2),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.dietary_trends OWNER TO postgres;

--
-- Name: feature_popularity; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.feature_popularity (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    feature text NOT NULL,
    platform text,
    lang character(2),
    year integer NOT NULL,
    month_number integer NOT NULL,
    usage_count integer DEFAULT 0,
    unique_users integer DEFAULT 0,
    avg_duration_ms integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.feature_popularity OWNER TO postgres;

--
-- Name: llm_quality; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.llm_quality (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    year integer NOT NULL,
    week_number integer NOT NULL,
    lang character(2),
    detected_intent text,
    total_interactions integer DEFAULT 0,
    avg_response_ms integer,
    avg_products_returned numeric(6,1),
    saves_from_chat integer DEFAULT 0,
    follow_up_count integer DEFAULT 0,
    zero_product_returns integer DEFAULT 0,
    avg_tokens_in integer,
    avg_tokens_out integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.llm_quality OWNER TO postgres;

--
-- Name: price_analytics; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.price_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    product_name text,
    category text,
    year integer NOT NULL,
    week_number integer NOT NULL,
    avg_price_chf numeric(10,2),
    min_price_chf numeric(10,2),
    max_price_chf numeric(10,2),
    price_changes integer DEFAULT 0,
    promotion_days integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.price_analytics OWNER TO postgres;

--
-- Name: product_performance; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.product_performance (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    product_name text,
    category text,
    year integer NOT NULL,
    month_number integer NOT NULL,
    total_scans integer DEFAULT 0,
    total_searches integer DEFAULT 0,
    total_saves integer DEFAULT 0,
    total_views integer DEFAULT 0,
    total_chat_mentions integer DEFAULT 0,
    total_feedback integer DEFAULT 0,
    positive_feedback integer DEFAULT 0,
    negative_feedback integer DEFAULT 0,
    dispute_count integer DEFAULT 0,
    avg_price_chf numeric(10,2),
    min_price_chf numeric(10,2),
    max_price_chf numeric(10,2),
    promotion_days integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.product_performance OWNER TO postgres;

--
-- Name: rebuild_log; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.rebuild_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    job_name text NOT NULL,
    status text DEFAULT 'running'::text,
    rows_processed integer DEFAULT 0,
    started_at timestamp with time zone DEFAULT now(),
    finished_at timestamp with time zone,
    error text,
    CONSTRAINT rebuild_log_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text])))
);


ALTER TABLE analytics.rebuild_log OWNER TO postgres;

--
-- Name: retention_cohorts; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.retention_cohorts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cohort_week integer NOT NULL,
    cohort_year integer NOT NULL,
    users_acquired integer DEFAULT 0,
    retained_w1 integer DEFAULT 0,
    retained_w2 integer DEFAULT 0,
    retained_w4 integer DEFAULT 0,
    retained_w8 integer DEFAULT 0,
    retained_w12 integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.retention_cohorts OWNER TO postgres;

--
-- Name: search_patterns; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.search_patterns (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    year integer NOT NULL,
    week_number integer NOT NULL,
    lang character(2),
    total_searches integer DEFAULT 0,
    unique_queries integer DEFAULT 0,
    zero_result_count integer DEFAULT 0,
    avg_results_count numeric(6,1),
    top_queries jsonb DEFAULT '[]'::jsonb,
    top_filters jsonb DEFAULT '{}'::jsonb,
    click_through_rate numeric(5,2),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.search_patterns OWNER TO postgres;

--
-- Name: session_quality; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.session_quality (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    year integer NOT NULL,
    week_number integer NOT NULL,
    platform text,
    lang character(2),
    total_sessions integer DEFAULT 0,
    avg_duration_secs numeric(8,1),
    avg_events_per_session numeric(6,1),
    bounce_count integer DEFAULT 0,
    found_product_count integer DEFAULT 0,
    avg_scans_per_session numeric(6,1),
    avg_searches_per_session numeric(6,1),
    avg_chats_per_session numeric(6,1),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.session_quality OWNER TO postgres;

--
-- Name: swiss_regional; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.swiss_regional (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    region text NOT NULL,
    lang character(2),
    dietary_type text,
    year integer NOT NULL,
    month_number integer NOT NULL,
    scan_count integer DEFAULT 0,
    search_count integer DEFAULT 0,
    top_category text,
    top_store text,
    avg_price_sensitivity numeric(5,2),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT swiss_regional_region_check CHECK ((region = ANY (ARRAY['zurich'::text, 'bern'::text, 'basel'::text, 'geneva'::text, 'lausanne'::text, 'lugano'::text, 'lucerne'::text, 'st_gallen'::text, 'winterthur'::text, 'other'::text])))
);


ALTER TABLE analytics.swiss_regional OWNER TO postgres;

--
-- Name: user_growth; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.user_growth (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    week_start date NOT NULL,
    year integer NOT NULL,
    week_number integer NOT NULL,
    new_users integer DEFAULT 0,
    logins integer DEFAULT 0,
    active_users integer DEFAULT 0,
    scan_users integer DEFAULT 0,
    search_users integer DEFAULT 0,
    chat_users integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.user_growth OWNER TO postgres;

--
-- Name: verdict_analytics; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.verdict_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    verdict_key text NOT NULL,
    store text,
    lang character(2),
    year integer NOT NULL,
    month_number integer NOT NULL,
    request_count integer DEFAULT 0,
    positive_count integer DEFAULT 0,
    negative_count integer DEFAULT 0,
    dispute_count integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.verdict_analytics OWNER TO postgres;

--
-- Name: verdict_disputes; Type: TABLE; Schema: analytics; Owner: postgres
--

CREATE TABLE analytics.verdict_disputes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    verdict_key text NOT NULL,
    year integer NOT NULL,
    month_number integer NOT NULL,
    dispute_count integer DEFAULT 0,
    resolved_count integer DEFAULT 0,
    ontology_updated boolean DEFAULT false,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE analytics.verdict_disputes OWNER TO postgres;

--
-- Name: ontology_improvement_queue; Type: TABLE; Schema: etl; Owner: postgres
--

CREATE TABLE etl.ontology_improvement_queue (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source text NOT NULL,
    ontology_group text NOT NULL,
    suggested_term text NOT NULL,
    lang text DEFAULT 'en'::text NOT NULL,
    reason text,
    gtin character varying(50),
    store text,
    priority integer DEFAULT 3,
    status text DEFAULT 'pending'::text,
    created_at timestamp with time zone DEFAULT now(),
    reviewed_at timestamp with time zone,
    reviewed_by text,
    CONSTRAINT ontology_improvement_queue_priority_check CHECK (((priority >= 1) AND (priority <= 5))),
    CONSTRAINT ontology_improvement_queue_source_check CHECK ((source = ANY (ARRAY['user_feedback'::text, 'llm_interaction'::text, 'admin_review'::text, 'automated_scan'::text, 'scraper'::text]))),
    CONSTRAINT ontology_improvement_queue_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'added'::text])))
);


ALTER TABLE etl.ontology_improvement_queue OWNER TO postgres;

--
-- Name: scrape_failures; Type: TABLE; Schema: etl; Owner: postgres
--

CREATE TABLE etl.scrape_failures (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    job_id uuid,
    store character varying(50),
    url text,
    gtin character varying(50),
    error_type text,
    error_message text,
    http_status integer,
    retry_count integer DEFAULT 0,
    is_resolved boolean DEFAULT false,
    occurred_at timestamp with time zone DEFAULT now(),
    CONSTRAINT scrape_failures_error_type_check CHECK ((error_type = ANY (ARRAY['http_error'::text, 'parse_error'::text, 'timeout'::text, 'blocked'::text, 'schema_mismatch'::text, 'validation_error'::text, 'not_found'::text])))
);


ALTER TABLE etl.scrape_failures OWNER TO postgres;

--
-- Name: scraper_change_log; Type: TABLE; Schema: etl; Owner: postgres
--

CREATE TABLE etl.scraper_change_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    job_id uuid,
    gtin character varying(50) NOT NULL,
    store character varying(50) NOT NULL,
    change_type text NOT NULL,
    field_name text,
    old_value text,
    new_value text,
    changed_at timestamp with time zone DEFAULT now(),
    CONSTRAINT scraper_change_log_change_type_check CHECK ((change_type = ANY (ARRAY['price_change'::text, 'new_product'::text, 'product_deactivated'::text, 'ingredient_change'::text, 'allergen_change'::text, 'ontology_tag_change'::text, 'name_change'::text, 'image_change'::text])))
);


ALTER TABLE etl.scraper_change_log OWNER TO postgres;

--
-- Name: scraper_jobs; Type: TABLE; Schema: etl; Owner: postgres
--

CREATE TABLE etl.scraper_jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    store character varying(50) NOT NULL,
    job_type text NOT NULL,
    status text DEFAULT 'queued'::text NOT NULL,
    triggered_by text DEFAULT 'scheduler'::text,
    products_found integer DEFAULT 0,
    products_created integer DEFAULT 0,
    products_updated integer DEFAULT 0,
    prices_updated integer DEFAULT 0,
    failures_count integer DEFAULT 0,
    queued_at timestamp with time zone DEFAULT now(),
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    duration_ms integer,
    error_summary text,
    log_url text,
    meta jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT scraper_jobs_job_type_check CHECK ((job_type = ANY (ARRAY['full_catalogue'::text, 'price_update'::text, 'new_products'::text, 'ingredient_update'::text, 'certification_check'::text]))),
    CONSTRAINT scraper_jobs_status_check CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'completed'::text, 'failed'::text, 'partial'::text]))),
    CONSTRAINT scraper_jobs_triggered_by_check CHECK ((triggered_by = ANY (ARRAY['scheduler'::text, 'manual'::text, 'webhook'::text, 'retry'::text])))
);


ALTER TABLE etl.scraper_jobs OWNER TO postgres;

--
-- Name: scraper_sources; Type: TABLE; Schema: etl; Owner: postgres
--

CREATE TABLE etl.scraper_sources (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    store character varying(50) NOT NULL,
    base_url text NOT NULL,
    scrape_type text NOT NULL,
    schedule_cron text DEFAULT '0 3 * * *'::text NOT NULL,
    is_active boolean DEFAULT true,
    requires_proxy boolean DEFAULT false,
    rate_limit_rps numeric(4,2) DEFAULT 1.0,
    last_success_at timestamp with time zone,
    last_attempt_at timestamp with time zone,
    consecutive_failures integer DEFAULT 0,
    config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT scraper_sources_scrape_type_check CHECK ((scrape_type = ANY (ARRAY['playwright'::text, 'httpx_bs4'::text, 'api'::text, 'rss'::text, 'pdf'::text])))
);


ALTER TABLE etl.scraper_sources OWNER TO postgres;

--
-- Name: staging_products; Type: TABLE; Schema: etl; Owner: postgres
--

CREATE TABLE etl.staging_products (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    job_id uuid,
    store character varying(50) NOT NULL,
    gtin character varying(50),
    raw_payload jsonb NOT NULL,
    parsed_payload jsonb,
    validation_errors jsonb DEFAULT '[]'::jsonb,
    status text DEFAULT 'pending'::text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT staging_products_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'valid'::text, 'invalid'::text, 'promoted'::text, 'skipped'::text])))
);


ALTER TABLE etl.staging_products OWNER TO postgres;

--
-- Name: allergen_alert_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.allergen_alert_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_id uuid,
    gtin character varying(50) NOT NULL,
    store text,
    category text,
    allergen_type text NOT NULL,
    alert_type text NOT NULL,
    user_has_allergy boolean DEFAULT false,
    lang character(2),
    platform text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT allergen_alert_events_alert_type_check CHECK ((alert_type = ANY (ARRAY['contains'::text, 'may_contain'::text, 'conflict'::text])))
);


ALTER TABLE events.allergen_alert_events OWNER TO postgres;

--
-- Name: api_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.api_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    api_key_hash text,
    client_name text,
    endpoint text NOT NULL,
    method text NOT NULL,
    status_code integer,
    response_ms integer,
    lang character(2),
    platform text,
    gtin character varying(50),
    error_type text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE events.api_events OWNER TO postgres;

--
-- Name: chat_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.chat_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_id uuid,
    mode text NOT NULL,
    lang character(2),
    platform text,
    is_anonymous boolean DEFAULT false,
    question_length integer,
    question_word_count integer,
    detected_intent text,
    detected_dietary text,
    detected_store text,
    detected_category text,
    detected_price_filter boolean DEFAULT false,
    llm_called boolean DEFAULT false,
    llm_model text,
    llm_tokens_in integer,
    llm_tokens_out integer,
    response_time_ms integer,
    answer_length integer,
    products_returned integer DEFAULT 0,
    verdicts_used jsonb DEFAULT '[]'::jsonb,
    user_followed_up boolean DEFAULT false,
    user_saved_result boolean DEFAULT false,
    user_gave_feedback boolean DEFAULT false,
    led_to_scan boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chat_events_mode_check CHECK ((mode = ANY (ARRAY['chat'::text, 'voice'::text]))),
    CONSTRAINT chat_events_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE events.chat_events OWNER TO postgres;

--
-- Name: error_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.error_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid,
    user_id uuid,
    error_type text NOT NULL,
    endpoint text,
    platform text,
    lang character(2),
    error_message text,
    stack_trace text,
    gtin character varying(50),
    store text,
    http_status integer,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE events.error_events OWNER TO postgres;

--
-- Name: feature_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.feature_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_id uuid,
    feature text NOT NULL,
    platform text,
    lang character(2),
    duration_ms integer,
    is_anonymous boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT feature_events_feature_check CHECK ((feature = ANY (ARRAY['barcode_scan'::text, 'manual_search'::text, 'voice_search'::text, 'chat_ask'::text, 'filter_halal'::text, 'filter_vegan'::text, 'filter_gluten_free'::text, 'filter_lactose_free'::text, 'filter_organic'::text, 'filter_price'::text, 'filter_store'::text, 'save_product'::text, 'create_list'::text, 'add_to_list'::text, 'share_product'::text, 'compare_stores'::text, 'price_history_view'::text, 'verdict_detail'::text, 'preferences_setup'::text, 'price_calculator'::text, 'basket_calculator'::text, 'promotion_browse'::text]))),
    CONSTRAINT feature_events_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE events.feature_events OWNER TO postgres;

--
-- Name: feedback_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.feedback_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    gtin character varying(50) NOT NULL,
    store text,
    verdict_key text NOT NULL,
    our_verdict boolean NOT NULL,
    user_claims boolean NOT NULL,
    is_dispute boolean GENERATED ALWAYS AS ((our_verdict <> user_claims)) STORED,
    comment text,
    lang character(2),
    platform text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE events.feedback_events OWNER TO postgres;

--
-- Name: price_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.price_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    product_name text,
    category text,
    event_type text NOT NULL,
    old_price_chf numeric(10,2),
    new_price_chf numeric(10,2),
    change_pct numeric(5,2),
    is_promotion boolean DEFAULT false,
    price_date date DEFAULT CURRENT_DATE NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT price_events_event_type_check CHECK ((event_type = ANY (ARRAY['price_scraped'::text, 'price_changed'::text, 'promotion_started'::text, 'promotion_ended'::text, 'product_out_of_stock'::text, 'product_back_in_stock'::text])))
);


ALTER TABLE events.price_events OWNER TO postgres;

--
-- Name: product_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.product_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_id uuid,
    gtin character varying(50) NOT NULL,
    store text,
    category text,
    event_type text NOT NULL,
    verdict_key text,
    lang character(2),
    platform text,
    is_anonymous boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT product_events_event_type_check CHECK ((event_type = ANY (ARRAY['view'::text, 'save'::text, 'unsave'::text, 'list_add'::text, 'list_remove'::text, 'price_view'::text, 'verdict_view'::text, 'share'::text, 'compare_add'::text]))),
    CONSTRAINT product_events_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE events.product_events OWNER TO postgres;

--
-- Name: scan_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.scan_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_id uuid,
    gtin character varying(50) NOT NULL,
    store text,
    product_name text,
    category text,
    lang character(2),
    platform text,
    is_anonymous boolean DEFAULT false,
    product_found boolean DEFAULT false,
    verdicts_shown jsonb DEFAULT '[]'::jsonb,
    price_shown boolean DEFAULT false,
    led_to_save boolean DEFAULT false,
    led_to_feedback boolean DEFAULT false,
    led_to_chat boolean DEFAULT false,
    duration_ms integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT scan_events_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE events.scan_events OWNER TO postgres;

--
-- Name: search_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.search_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_id uuid,
    query text,
    filters jsonb DEFAULT '{}'::jsonb,
    results_count integer DEFAULT 0,
    has_zero_results boolean DEFAULT false,
    lang character(2),
    platform text,
    is_anonymous boolean DEFAULT false,
    clicked_gtin character varying(50),
    clicked_store text,
    clicked_position integer,
    led_to_save boolean DEFAULT false,
    led_to_scan boolean DEFAULT false,
    led_to_chat boolean DEFAULT false,
    is_refinement boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT search_events_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE events.search_events OWNER TO postgres;

--
-- Name: session_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.session_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    user_id uuid,
    event_type text NOT NULL,
    platform text,
    lang character(2),
    duration_seconds integer,
    bounced boolean DEFAULT false,
    found_product boolean DEFAULT false,
    entry_point text,
    exit_point text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT session_events_event_type_check CHECK ((event_type = ANY (ARRAY['session_start'::text, 'session_end'::text]))),
    CONSTRAINT session_events_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE events.session_events OWNER TO postgres;

--
-- Name: user_events; Type: TABLE; Schema: events; Owner: postgres
--

CREATE TABLE events.user_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_id uuid,
    event_type text NOT NULL,
    platform text,
    lang character(2),
    is_anonymous boolean DEFAULT false,
    meta jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_events_event_type_check CHECK ((event_type = ANY (ARRAY['signup'::text, 'login'::text, 'logout'::text, 'preference_update'::text, 'consent_update'::text, 'account_delete_request'::text]))),
    CONSTRAINT user_events_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE events.user_events OWNER TO postgres;

--
-- Name: agent_execution_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_execution_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid,
    user_id uuid,
    input_type text NOT NULL,
    raw_input text,
    lang character(2) DEFAULT 'en'::bpchar,
    platform text,
    intent_detected text,
    agents_called jsonb DEFAULT '[]'::jsonb,
    data_sources_hit jsonb DEFAULT '[]'::jsonb,
    llm_called boolean DEFAULT false,
    llm_tokens_in integer,
    llm_tokens_out integer,
    llm_model text,
    total_duration_ms integer,
    db_duration_ms integer,
    llm_duration_ms integer,
    products_returned integer DEFAULT 0,
    verdicts_returned integer DEFAULT 0,
    error text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT agent_execution_log_input_type_check CHECK ((input_type = ANY (ARRAY['barcode'::text, 'voice'::text, 'chat'::text, 'search'::text]))),
    CONSTRAINT agent_execution_log_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE public.agent_execution_log OWNER TO postgres;

--
-- Name: allergen_alert_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.allergen_alert_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    allergen_type text NOT NULL,
    alert_count integer DEFAULT 0,
    unique_users integer DEFAULT 0,
    category text,
    lang character(2),
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.allergen_alert_analytics OWNER TO postgres;

--
-- Name: allergen_risk_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.allergen_risk_summary AS
 SELECT allergen_type,
    sum(alert_count) AS total_alerts,
    sum(unique_users) AS total_users_warned,
    count(DISTINCT gtin) AS products_affected,
    count(DISTINCT store) AS stores_affected,
    max(updated_at) AS last_seen
   FROM public.allergen_alert_analytics
  GROUP BY allergen_type
  ORDER BY (sum(alert_count)) DESC;


ALTER VIEW public.allergen_risk_summary OWNER TO postgres;

--
-- Name: api_usage_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_usage_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    api_key_hash text,
    endpoint text NOT NULL,
    method text NOT NULL,
    status_code integer,
    response_time_ms integer,
    request_lang character(2),
    platform text,
    error_type text,
    week_number integer,
    month_number integer,
    year integer,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.api_usage_analytics OWNER TO postgres;

--
-- Name: app_behaviour_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.app_behaviour_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid,
    user_id uuid,
    platform text,
    lang character(2),
    used_scan boolean DEFAULT false,
    used_search boolean DEFAULT false,
    used_chat boolean DEFAULT false,
    scan_count integer DEFAULT 0,
    scan_to_save_count integer DEFAULT 0,
    scan_to_feedback_count integer DEFAULT 0,
    avg_scan_duration_ms integer,
    search_count integer DEFAULT 0,
    search_refined_count integer DEFAULT 0,
    search_zero_results integer DEFAULT 0,
    search_to_save_count integer DEFAULT 0,
    avg_search_result_count numeric(6,1),
    chat_count integer DEFAULT 0,
    chat_follow_up_count integer DEFAULT 0,
    chat_to_scan_count integer DEFAULT 0,
    chat_to_save_count integer DEFAULT 0,
    avg_chat_length_chars integer,
    avg_response_length_chars integer,
    screens_visited jsonb DEFAULT '[]'::jsonb,
    most_used_feature text,
    entry_point text,
    exit_point text,
    week_number integer,
    month_number integer,
    year integer,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.app_behaviour_analytics OWNER TO postgres;

--
-- Name: app_mode_usage; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.app_mode_usage AS
 SELECT platform,
    lang,
    sum(
        CASE
            WHEN used_scan THEN 1
            ELSE 0
        END) AS scan_sessions,
    sum(
        CASE
            WHEN used_search THEN 1
            ELSE 0
        END) AS search_sessions,
    sum(
        CASE
            WHEN used_chat THEN 1
            ELSE 0
        END) AS chat_sessions,
    sum(scan_count) AS total_scans,
    sum(search_count) AS total_searches,
    sum(chat_count) AS total_chats,
    round(avg(avg_scan_duration_ms)) AS avg_scan_ms,
    sum(search_zero_results) AS zero_result_searches,
    sum(chat_follow_up_count) AS chat_follow_ups
   FROM public.app_behaviour_analytics
  GROUP BY platform, lang
  ORDER BY (sum(scan_count)) DESC;


ALTER VIEW public.app_mode_usage OWNER TO postgres;

--
-- Name: b2b_report_access_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.b2b_report_access_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    client_name text NOT NULL,
    client_type text,
    report_type text NOT NULL,
    date_range_start date,
    date_range_end date,
    records_accessed integer,
    is_anonymised boolean DEFAULT true,
    accessed_at timestamp with time zone DEFAULT now(),
    api_key_hash text,
    CONSTRAINT b2b_report_access_log_client_type_check CHECK ((client_type = ANY (ARRAY['retailer'::text, 'food_brand'::text, 'health_insurer'::text, 'academic'::text, 'government'::text, 'other'::text])))
);


ALTER TABLE public.b2b_report_access_log OWNER TO postgres;

--
-- Name: barcode_aliases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.barcode_aliases (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    raw_barcode text NOT NULL,
    normalized_gtin character varying(50) NOT NULL,
    barcode_format text,
    retailer text,
    confidence numeric(3,2) DEFAULT 1.0,
    is_verified boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT barcode_aliases_barcode_format_check CHECK ((barcode_format = ANY (ARRAY['EAN13'::text, 'EAN8'::text, 'UPC_A'::text, 'UPC_E'::text, 'QR'::text, 'DATAMATRIX'::text, 'internal'::text]))),
    CONSTRAINT barcode_aliases_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))
);


ALTER TABLE public.barcode_aliases OWNER TO postgres;

--
-- Name: category_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.category_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    category text NOT NULL,
    store text,
    lang character(2),
    scan_count integer DEFAULT 0,
    search_count integer DEFAULT 0,
    save_count integer DEFAULT 0,
    avg_price_chf numeric(10,2),
    top_verdict text,
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.category_analytics OWNER TO postgres;

--
-- Name: consent_audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.consent_audit_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    consent_type text NOT NULL,
    action text NOT NULL,
    consent_version text NOT NULL,
    ip_hash text,
    platform text,
    lang character(2),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT consent_audit_log_action_check CHECK ((action = ANY (ARRAY['granted'::text, 'withdrawn'::text, 'updated'::text, 'viewed'::text]))),
    CONSTRAINT consent_audit_log_consent_type_check CHECK ((consent_type = ANY (ARRAY['data_collection'::text, 'analytics'::text, 'marketing'::text, 'chat_history'::text, 'dietary_profile'::text, 'third_party_sharing'::text])))
);


ALTER TABLE public.consent_audit_log OWNER TO postgres;

--
-- Name: data_access_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.data_access_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    accessed_by text NOT NULL,
    data_type text NOT NULL,
    reason text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT data_access_log_accessed_by_check CHECK ((accessed_by = ANY (ARRAY['user'::text, 'admin'::text, 'system'::text, 'api'::text])))
);


ALTER TABLE public.data_access_log OWNER TO postgres;

--
-- Name: data_deletion_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.data_deletion_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    requested_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    deleted_tables jsonb DEFAULT '[]'::jsonb,
    status text DEFAULT 'pending'::text,
    requested_via text,
    notes text,
    CONSTRAINT data_deletion_log_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'in_progress'::text, 'completed'::text, 'failed'::text])))
);


ALTER TABLE public.data_deletion_log OWNER TO postgres;

--
-- Name: dietary_trend_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dietary_trend_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dietary_type text NOT NULL,
    region text,
    lang character(2),
    user_count integer DEFAULT 0,
    scan_count integer DEFAULT 0,
    search_count integer DEFAULT 0,
    growth_pct numeric(5,2),
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.dietary_trend_analytics OWNER TO postgres;

--
-- Name: verdict_dispute_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.verdict_dispute_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    product_name text,
    verdict_key text NOT NULL,
    our_verdict boolean NOT NULL,
    user_claims boolean NOT NULL,
    dispute_count integer DEFAULT 0,
    resolved boolean DEFAULT false,
    resolution text,
    ontology_updated boolean DEFAULT false,
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.verdict_dispute_analytics OWNER TO postgres;

--
-- Name: disputed_verdicts_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.disputed_verdicts_summary AS
 SELECT verdict_key,
    store,
    sum(dispute_count) AS total_disputes,
    sum(
        CASE
            WHEN resolved THEN 1
            ELSE 0
        END) AS resolved_count,
    sum(
        CASE
            WHEN ontology_updated THEN 1
            ELSE 0
        END) AS ontology_fixes,
    round((((sum(
        CASE
            WHEN resolved THEN 1
            ELSE 0
        END))::numeric / (NULLIF(sum(dispute_count), 0))::numeric) * (100)::numeric), 1) AS resolution_rate_pct
   FROM public.verdict_dispute_analytics
  GROUP BY verdict_key, store
  ORDER BY (sum(dispute_count)) DESC;


ALTER VIEW public.disputed_verdicts_summary OWNER TO postgres;

--
-- Name: error_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.error_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    error_type text NOT NULL,
    endpoint text,
    platform text,
    lang character(2),
    error_message text,
    gtin character varying(50),
    store text,
    count integer DEFAULT 1,
    first_seen_at timestamp with time zone DEFAULT now(),
    last_seen_at timestamp with time zone DEFAULT now(),
    resolved boolean DEFAULT false,
    week_number integer,
    month_number integer,
    year integer
);


ALTER TABLE public.error_analytics OWNER TO postgres;

--
-- Name: feature_usage_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feature_usage_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    feature text NOT NULL,
    platform text,
    lang character(2),
    usage_count integer DEFAULT 0,
    unique_users integer DEFAULT 0,
    avg_time_spent_ms integer,
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT feature_usage_analytics_feature_check CHECK ((feature = ANY (ARRAY['barcode_scan'::text, 'manual_search'::text, 'chat_ask'::text, 'filter_halal'::text, 'filter_vegan'::text, 'filter_gluten_free'::text, 'filter_lactose_free'::text, 'filter_bio'::text, 'filter_price'::text, 'filter_store'::text, 'save_product'::text, 'create_list'::text, 'share_product'::text, 'compare_stores'::text, 'price_history'::text, 'verdict_detail'::text, 'preferences_setup'::text])))
);


ALTER TABLE public.feature_usage_analytics OWNER TO postgres;

--
-- Name: feature_popularity; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.feature_popularity AS
 SELECT feature,
    platform,
    sum(usage_count) AS total_usage,
    sum(unique_users) AS total_users,
    round(avg(avg_time_spent_ms)) AS avg_time_ms
   FROM public.feature_usage_analytics
  GROUP BY feature, platform
  ORDER BY (sum(usage_count)) DESC;


ALTER VIEW public.feature_popularity OWNER TO postgres;

--
-- Name: llm_interaction_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.llm_interaction_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid,
    mode text,
    lang character(2),
    platform text,
    question_length integer,
    question_word_count integer,
    detected_intent text,
    detected_dietary text,
    detected_store text,
    detected_category text,
    detected_price_filter boolean DEFAULT false,
    answer_length integer,
    products_returned integer DEFAULT 0,
    verdicts_used jsonb DEFAULT '[]'::jsonb,
    response_time_ms integer,
    user_followed_up boolean DEFAULT false,
    user_saved_result boolean DEFAULT false,
    user_gave_feedback boolean DEFAULT false,
    week_number integer,
    month_number integer,
    year integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT llm_interaction_analytics_mode_check CHECK ((mode = ANY (ARRAY['scan'::text, 'search'::text, 'chat'::text])))
);


ALTER TABLE public.llm_interaction_analytics OWNER TO postgres;

--
-- Name: llm_quality_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.llm_quality_summary AS
 SELECT detected_intent,
    lang,
    count(*) AS total_interactions,
    round(avg(response_time_ms)) AS avg_response_ms,
    round(avg(products_returned), 1) AS avg_products_returned,
    sum(
        CASE
            WHEN user_saved_result THEN 1
            ELSE 0
        END) AS saves_from_chat,
    sum(
        CASE
            WHEN user_followed_up THEN 1
            ELSE 0
        END) AS follow_up_count,
    round((((sum(
        CASE
            WHEN user_saved_result THEN 1
            ELSE 0
        END))::numeric / (NULLIF(count(*), 0))::numeric) * (100)::numeric), 1) AS save_conversion_pct
   FROM public.llm_interaction_analytics
  GROUP BY detected_intent, lang
  ORDER BY (count(*)) DESC;


ALTER VIEW public.llm_quality_summary OWNER TO postgres;

--
-- Name: nutrition_facts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.nutrition_facts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    product_id uuid NOT NULL,
    energy_kcal_100 numeric(8,2),
    energy_kj_100 numeric(8,2),
    fat_100 numeric(8,2),
    saturated_fat_100 numeric(8,2),
    carbs_100 numeric(8,2),
    sugars_100 numeric(8,2),
    fibre_100 numeric(8,2),
    protein_100 numeric(8,2),
    salt_100 numeric(8,2),
    sodium_100 numeric(8,2),
    serving_size_g numeric(8,2),
    energy_kcal_srv numeric(8,2),
    fat_srv numeric(8,2),
    carbs_srv numeric(8,2),
    sugars_srv numeric(8,2),
    protein_srv numeric(8,2),
    salt_srv numeric(8,2),
    vitamins jsonb,
    minerals jsonb,
    nutri_score character(1),
    nova_group integer,
    source text DEFAULT 'scraper'::text,
    last_updated timestamp with time zone DEFAULT now(),
    CONSTRAINT nutrition_facts_nova_group_check CHECK (((nova_group >= 1) AND (nova_group <= 4))),
    CONSTRAINT nutrition_facts_nutri_score_check CHECK ((nutri_score = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar, 'D'::bpchar, 'E'::bpchar])))
);


ALTER TABLE public.nutrition_facts OWNER TO postgres;

--
-- Name: ontology_current; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ontology_current (
    lock boolean DEFAULT true NOT NULL,
    version character varying(20) NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT only_one_row CHECK ((lock = true))
);


ALTER TABLE public.ontology_current OWNER TO postgres;

--
-- Name: ontology_improvement_queue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ontology_improvement_queue (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source text NOT NULL,
    ontology_group text NOT NULL,
    suggested_term text NOT NULL,
    lang text NOT NULL,
    reason text,
    gtin character varying(50),
    store text,
    status text DEFAULT 'pending'::text,
    priority integer DEFAULT 3,
    created_at timestamp with time zone DEFAULT now(),
    reviewed_at timestamp with time zone,
    reviewed_by text,
    CONSTRAINT ontology_improvement_queue_priority_check CHECK (((priority >= 1) AND (priority <= 5))),
    CONSTRAINT ontology_improvement_queue_source_check CHECK ((source = ANY (ARRAY['user_feedback'::text, 'llm_interaction'::text, 'admin_review'::text, 'automated_scan'::text]))),
    CONSTRAINT ontology_improvement_queue_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'added'::text])))
);


ALTER TABLE public.ontology_improvement_queue OWNER TO postgres;

--
-- Name: ontology_priority_queue; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.ontology_priority_queue AS
 SELECT ontology_group,
    lang,
    count(*) AS pending_suggestions,
    sum(
        CASE
            WHEN (priority = 1) THEN 1
            ELSE 0
        END) AS urgent_count,
    sum(
        CASE
            WHEN (priority = 2) THEN 1
            ELSE 0
        END) AS high_count,
    max(created_at) AS latest_suggestion
   FROM public.ontology_improvement_queue
  WHERE (status = 'pending'::text)
  GROUP BY ontology_group, lang
  ORDER BY (sum(
        CASE
            WHEN (priority = 1) THEN 1
            ELSE 0
        END)) DESC, (count(*)) DESC;


ALTER VIEW public.ontology_priority_queue OWNER TO postgres;

--
-- Name: ontology_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ontology_versions (
    version character varying(20) NOT NULL,
    applied_at timestamp with time zone DEFAULT now(),
    notes text
);


ALTER TABLE public.ontology_versions OWNER TO postgres;

--
-- Name: price_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.price_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    product_name text,
    category text,
    price_chf numeric(10,2) NOT NULL,
    unit_price_chf numeric(10,2),
    is_promotion boolean DEFAULT false,
    promotion_info jsonb,
    price_date date NOT NULL,
    week_number integer,
    month_number integer,
    year integer,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.price_analytics OWNER TO postgres;

--
-- Name: price_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.price_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    product_id uuid NOT NULL,
    gtin character varying(50) NOT NULL,
    store character varying(50) NOT NULL,
    price_chf numeric(10,2) NOT NULL,
    price_per_100g numeric(10,4),
    is_promotion boolean DEFAULT false,
    discount_pct numeric(5,2),
    price_date date NOT NULL,
    recorded_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.price_history OWNER TO postgres;

--
-- Name: price_intelligence; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.price_intelligence AS
 SELECT gtin,
    store,
    product_name,
    category,
    price_chf,
    price_date,
    is_promotion,
    avg(price_chf) OVER (PARTITION BY gtin, store ORDER BY price_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS rolling_avg_4_weeks,
    min(price_chf) OVER (PARTITION BY gtin, store) AS all_time_low,
    max(price_chf) OVER (PARTITION BY gtin, store) AS all_time_high
   FROM public.price_analytics pa;


ALTER VIEW public.price_intelligence OWNER TO postgres;

--
-- Name: privacy_policy_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.privacy_policy_versions (
    version text NOT NULL,
    published_at timestamp with time zone DEFAULT now(),
    effective_at timestamp with time zone NOT NULL,
    summary_en text,
    summary_de text,
    summary_fr text,
    summary_it text,
    changes_en text,
    requires_new_consent boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.privacy_policy_versions OWNER TO postgres;

--
-- Name: product_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50),
    store text,
    category text,
    event_type text NOT NULL,
    verdict_key text,
    lang character(2),
    week_number integer,
    year integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT product_analytics_event_type_check CHECK ((event_type = ANY (ARRAY['scan'::text, 'search'::text, 'save'::text, 'feedback'::text, 'chat'::text])))
);


ALTER TABLE public.product_analytics OWNER TO postgres;

--
-- Name: product_performance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_performance (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store text NOT NULL,
    product_name text,
    category text,
    total_scans integer DEFAULT 0,
    total_searches integer DEFAULT 0,
    total_saves integer DEFAULT 0,
    total_chat_mentions integer DEFAULT 0,
    total_feedback integer DEFAULT 0,
    positive_feedback integer DEFAULT 0,
    negative_feedback integer DEFAULT 0,
    avg_price_chf numeric(10,2),
    min_price_chf numeric(10,2),
    max_price_chf numeric(10,2),
    last_scanned_at timestamp with time zone,
    last_price_change timestamp with time zone,
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.product_performance OWNER TO postgres;

--
-- Name: product_popularity; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.product_popularity AS
 SELECT gtin,
    store,
    product_name,
    category,
    total_scans,
    total_saves,
    total_searches,
    avg_price_chf,
    positive_feedback,
    negative_feedback,
        CASE
            WHEN (total_feedback > 0) THEN round((((positive_feedback)::numeric / (total_feedback)::numeric) * (100)::numeric), 1)
            ELSE NULL::numeric
        END AS positive_feedback_pct,
    ((total_scans + total_saves) + total_searches) AS engagement_score
   FROM public.product_performance pp
  ORDER BY ((total_scans + total_saves) + total_searches) DESC;


ALTER VIEW public.product_popularity OWNER TO postgres;

--
-- Name: product_prices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_prices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    product_id uuid NOT NULL,
    gtin character varying(50) NOT NULL,
    store character varying(50) NOT NULL,
    price_chf numeric(10,2) NOT NULL,
    currency character(3) DEFAULT 'CHF'::bpchar,
    unit_quantity numeric(10,3),
    unit_type text,
    price_per_100g numeric(10,4),
    pack_size_raw text,
    units_per_pack integer DEFAULT 1,
    price_per_pack_unit numeric(10,4),
    is_promotion boolean DEFAULT false,
    original_price_chf numeric(10,2),
    discount_pct numeric(5,2),
    promotion_label text,
    promotion_ends date,
    price_date date DEFAULT CURRENT_DATE NOT NULL,
    price_checked_at timestamp with time zone DEFAULT now(),
    CONSTRAINT product_prices_original_price_chf_check CHECK ((original_price_chf >= (0)::numeric)),
    CONSTRAINT product_prices_price_chf_check CHECK ((price_chf >= (0)::numeric)),
    CONSTRAINT product_prices_price_per_100g_check CHECK ((price_per_100g >= (0)::numeric)),
    CONSTRAINT product_prices_unit_type_check CHECK ((unit_type = ANY (ARRAY['g'::text, 'ml'::text, 'unit'::text, 'kg'::text, 'l'::text, 'cl'::text, 'oz'::text, 'lb'::text])))
);


ALTER TABLE public.product_prices OWNER TO postgres;

--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    store character varying(50) NOT NULL,
    name_en text,
    name_de text,
    name_fr text,
    name_it text,
    brand text,
    category text,
    sub_category text,
    image_url text,
    ingredients_raw text,
    ingredients_normalized jsonb,
    ontology_tags jsonb,
    allergens jsonb,
    nutrition_cache jsonb,
    pack_size_raw text,
    unit_quantity numeric(10,3),
    unit_type text,
    units_per_pack integer DEFAULT 1,
    ontology_version character varying(20),
    ontology_applied_at timestamp with time zone,
    ontology_needs_review boolean DEFAULT false,
    source_url text,
    scraped_at timestamp with time zone,
    scrape_checksum text,
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    verification_notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    image_source text,
    image_url_verified_at timestamp with time zone,
    image_url_is_dead boolean DEFAULT false,
    CONSTRAINT products_image_source_check CHECK ((image_source = ANY (ARRAY['retailer_url'::text, 'open_food_facts'::text, 'gs1'::text, 'internal'::text]))),
    CONSTRAINT products_unit_quantity_check CHECK ((unit_quantity > (0)::numeric)),
    CONSTRAINT products_unit_type_check CHECK ((unit_type = ANY (ARRAY['g'::text, 'ml'::text, 'unit'::text, 'kg'::text, 'l'::text, 'cl'::text, 'oz'::text, 'lb'::text])))
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: retention_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.retention_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cohort_week integer NOT NULL,
    cohort_year integer NOT NULL,
    users_acquired integer DEFAULT 0,
    retained_week_1 integer DEFAULT 0,
    retained_week_2 integer DEFAULT 0,
    retained_week_4 integer DEFAULT 0,
    retained_week_8 integer DEFAULT 0,
    retained_week_12 integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.retention_analytics OWNER TO postgres;

--
-- Name: search_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.search_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    query text,
    filters jsonb DEFAULT '{}'::jsonb,
    results_count integer DEFAULT 0,
    clicked_gtin character varying(50),
    clicked_store text,
    lang character(2),
    platform text,
    week_number integer,
    month_number integer,
    year integer,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.search_analytics OWNER TO postgres;

--
-- Name: session_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.session_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    user_id uuid,
    platform text,
    lang character(2),
    started_at timestamp with time zone DEFAULT now(),
    ended_at timestamp with time zone,
    duration_seconds integer,
    events_count integer DEFAULT 0,
    scans_count integer DEFAULT 0,
    searches_count integer DEFAULT 0,
    chats_count integer DEFAULT 0,
    saves_count integer DEFAULT 0,
    products_viewed integer DEFAULT 0,
    verdicts_viewed integer DEFAULT 0,
    found_product boolean DEFAULT false,
    bounced boolean DEFAULT false,
    week_number integer,
    month_number integer,
    year integer,
    CONSTRAINT session_analytics_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE public.session_analytics OWNER TO postgres;

--
-- Name: session_quality; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.session_quality AS
 SELECT platform,
    lang,
    count(*) AS total_sessions,
    round(avg(duration_seconds)) AS avg_duration_secs,
    round(avg(events_count), 1) AS avg_events,
    round(avg(scans_count), 1) AS avg_scans,
    round(avg(searches_count), 1) AS avg_searches,
    round(avg(chats_count), 1) AS avg_chats,
    sum(
        CASE
            WHEN bounced THEN 1
            ELSE 0
        END) AS bounces,
    round((((sum(
        CASE
            WHEN bounced THEN 1
            ELSE 0
        END))::numeric / (NULLIF(count(*), 0))::numeric) * (100)::numeric), 1) AS bounce_rate_pct,
    sum(
        CASE
            WHEN found_product THEN 1
            ELSE 0
        END) AS found_product_count
   FROM public.session_analytics
  GROUP BY platform, lang
  ORDER BY (count(*)) DESC;


ALTER VIEW public.session_quality OWNER TO postgres;

--
-- Name: store_comparison_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.store_comparison_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    product_name text,
    category text,
    migros_price numeric(10,2),
    coop_price numeric(10,2),
    aldi_price numeric(10,2),
    cheapest_store text,
    price_diff_pct numeric(5,2),
    comparison_date date NOT NULL,
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.store_comparison_analytics OWNER TO postgres;

--
-- Name: store_price_snapshot; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.store_price_snapshot (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gtin character varying(50) NOT NULL,
    snapshot_date date NOT NULL,
    prices_chf jsonb DEFAULT '{}'::jsonb NOT NULL,
    prices_per_100g jsonb DEFAULT '{}'::jsonb,
    cheapest_store text,
    cheapest_price numeric(10,2),
    most_expensive_store text,
    most_expensive_price numeric(10,2),
    price_spread_chf numeric(10,2),
    price_spread_pct numeric(5,2),
    stores_compared integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.store_price_snapshot OWNER TO postgres;

--
-- Name: swiss_regional_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.swiss_regional_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    region text NOT NULL,
    lang character(2),
    dietary_type text,
    scan_count integer DEFAULT 0,
    search_count integer DEFAULT 0,
    top_category text,
    top_store text,
    avg_price_sensitivity numeric(5,2),
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT swiss_regional_analytics_region_check CHECK ((region = ANY (ARRAY['zurich'::text, 'bern'::text, 'basel'::text, 'geneva'::text, 'lausanne'::text, 'lugano'::text, 'lucerne'::text, 'st_gallen'::text, 'winterthur'::text, 'other'::text])))
);


ALTER TABLE public.swiss_regional_analytics OWNER TO postgres;

--
-- Name: swiss_dietary_demand; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.swiss_dietary_demand AS
 SELECT region,
    dietary_type,
    sum(scan_count) AS total_scans,
    sum(search_count) AS total_searches,
    sum((scan_count + search_count)) AS total_demand,
    max(updated_at) AS last_updated
   FROM public.swiss_regional_analytics
  GROUP BY region, dietary_type
  ORDER BY (sum((scan_count + search_count))) DESC;


ALTER VIEW public.swiss_dietary_demand OWNER TO postgres;

--
-- Name: unified_product_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unified_product_members (
    unified_id uuid NOT NULL,
    product_id uuid NOT NULL,
    store character varying(50) NOT NULL,
    similarity_score numeric(5,4),
    match_method text,
    is_master boolean DEFAULT false,
    mapped_at timestamp with time zone DEFAULT now(),
    CONSTRAINT unified_product_members_match_method_check CHECK ((match_method = ANY (ARRAY['gtin_exact'::text, 'name_fuzzy'::text, 'manual'::text, 'llm'::text])))
);


ALTER TABLE public.unified_product_members OWNER TO postgres;

--
-- Name: unified_products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unified_products (
    unified_id uuid DEFAULT gen_random_uuid() NOT NULL,
    canonical_gtin character varying(50) NOT NULL,
    canonical_name_en text,
    canonical_name_de text,
    canonical_name_fr text,
    canonical_name_it text,
    canonical_brand text,
    canonical_category text,
    canonical_image_url text,
    master_product_id uuid,
    ontology_tags jsonb,
    allergens jsonb,
    total_scan_count integer DEFAULT 0,
    total_save_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.unified_products OWNER TO postgres;

--
-- Name: user_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    session_id uuid,
    event_type text NOT NULL,
    lang character(2),
    platform text,
    gtin character varying(50),
    store text,
    category text,
    verdict_key text,
    week_number integer,
    month_number integer,
    year integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_analytics_event_type_check CHECK ((event_type = ANY (ARRAY['signup'::text, 'login'::text, 'logout'::text, 'scan'::text, 'search'::text, 'chat'::text, 'save'::text, 'unsave'::text, 'list_create'::text, 'list_add'::text, 'list_remove'::text, 'feedback'::text, 'preference_update'::text, 'session_start'::text, 'session_end'::text, 'product_view'::text, 'verdict_view'::text, 'package_view'::text, 'price_view'::text]))),
    CONSTRAINT user_analytics_platform_check CHECK ((platform = ANY (ARRAY['web'::text, 'mobile'::text, 'api'::text])))
);


ALTER TABLE public.user_analytics OWNER TO postgres;

--
-- Name: user_chat_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_chat_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    session_id uuid,
    mode text NOT NULL,
    input text,
    filters jsonb DEFAULT '{}'::jsonb,
    response text,
    products_returned jsonb DEFAULT '[]'::jsonb,
    lang character(2) DEFAULT 'en'::bpchar,
    is_anonymous boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_chat_history_mode_check CHECK ((mode = ANY (ARRAY['scan'::text, 'search'::text, 'chat'::text, 'voice'::text])))
);


ALTER TABLE public.user_chat_history OWNER TO postgres;

--
-- Name: user_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_feedback (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    gtin character varying(50) NOT NULL,
    store text,
    verdict_key text NOT NULL,
    is_correct boolean NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_feedback OWNER TO postgres;

--
-- Name: user_growth; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.user_growth AS
 SELECT date_trunc('week'::text, created_at) AS week,
    count(*) FILTER (WHERE (event_type = 'signup'::text)) AS new_users,
    count(*) FILTER (WHERE (event_type = 'login'::text)) AS logins,
    count(*) FILTER (WHERE (event_type = 'scan'::text)) AS scans,
    count(*) FILTER (WHERE (event_type = 'search'::text)) AS searches,
    count(*) FILTER (WHERE (event_type = 'chat'::text)) AS chats,
    count(DISTINCT user_id) AS active_users
   FROM public.user_analytics
  GROUP BY (date_trunc('week'::text, created_at))
  ORDER BY (date_trunc('week'::text, created_at)) DESC;


ALTER VIEW public.user_growth OWNER TO postgres;

--
-- Name: user_list_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_list_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    list_id uuid,
    gtin character varying(50) NOT NULL,
    store text,
    product_name text,
    quantity integer DEFAULT 1,
    notes text,
    added_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_list_items_quantity_check CHECK ((quantity > 0))
);


ALTER TABLE public.user_list_items OWNER TO postgres;

--
-- Name: user_lists; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_lists (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_lists OWNER TO postgres;

--
-- Name: user_preferences; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_preferences (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    lang character(2) DEFAULT 'en'::bpchar,
    halal boolean DEFAULT false,
    vegan boolean DEFAULT false,
    vegetarian boolean DEFAULT false,
    gluten_free boolean DEFAULT false,
    lactose_free boolean DEFAULT false,
    keto boolean DEFAULT false,
    low_sugar boolean DEFAULT false,
    low_fat boolean DEFAULT false,
    high_protein boolean DEFAULT false,
    nut_allergy boolean DEFAULT false,
    dairy_free boolean DEFAULT false,
    preferred_stores jsonb DEFAULT '[]'::jsonb,
    excluded_stores jsonb DEFAULT '[]'::jsonb,
    max_price_chf numeric(10,2),
    price_sensitivity jsonb DEFAULT '{}'::jsonb,
    consent_data boolean DEFAULT false,
    consent_analytics boolean DEFAULT false,
    consent_marketing boolean DEFAULT false,
    consent_given_at timestamp with time zone,
    consent_version text DEFAULT 'v1.0'::text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_preferences_max_price_chf_check CHECK ((max_price_chf >= (0)::numeric))
);


ALTER TABLE public.user_preferences OWNER TO postgres;

--
-- Name: user_saved_products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_saved_products (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    gtin character varying(50) NOT NULL,
    store text,
    product_name text,
    notes text,
    saved_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_saved_products OWNER TO postgres;

--
-- Name: user_scans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_scans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    gtin character varying(50) NOT NULL,
    store text,
    product_name text,
    lang character(2) DEFAULT 'en'::bpchar,
    verdicts jsonb,
    is_anonymous boolean DEFAULT false,
    scanned_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_scans OWNER TO postgres;

--
-- Name: user_searches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_searches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    query text,
    filters jsonb DEFAULT '{}'::jsonb,
    results_count integer DEFAULT 0,
    lang character(2) DEFAULT 'en'::bpchar,
    is_anonymous boolean DEFAULT false,
    searched_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_searches OWNER TO postgres;

--
-- Name: v_active_promotions; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_active_promotions AS
 SELECT pp.gtin,
    pp.store,
    pr.name_en AS product_name,
    pr.brand,
    pr.category,
    pr.image_url,
    pp.price_chf AS promo_price,
    pp.original_price_chf,
    pp.discount_pct,
    pp.promotion_label,
    pp.promotion_ends,
    pp.price_per_100g
   FROM (public.product_prices pp
     JOIN public.products pr ON ((pr.id = pp.product_id)))
  WHERE ((pp.is_promotion = true) AND (pp.price_date = ( SELECT max(pp2.price_date) AS max
           FROM public.product_prices pp2
          WHERE (pp2.product_id = pp.product_id))) AND (pr.is_active = true))
  ORDER BY pp.discount_pct DESC NULLS LAST;


ALTER VIEW public.v_active_promotions OWNER TO postgres;

--
-- Name: VIEW v_active_promotions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_active_promotions IS 'All active promotions today, sorted by discount size.';


--
-- Name: v_allergen_risk; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_allergen_risk AS
 SELECT allergen_type,
    sum(alert_count) AS total_alerts,
    sum(unique_users) AS users_warned,
    sum(products_affected) AS products_affected,
    sum(stores_affected) AS stores_affected,
    sum(contains_count) AS definite_alerts,
    sum(may_contain_count) AS may_contain_alerts,
    sum(conflict_count) AS data_conflicts,
    max(updated_at) AS last_seen
   FROM analytics.allergen_risk
  GROUP BY allergen_type
  ORDER BY (sum(alert_count)) DESC;


ALTER VIEW public.v_allergen_risk OWNER TO postgres;

--
-- Name: v_api_performance; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_api_performance AS
 SELECT endpoint,
    sum(total_requests) AS total_requests,
    sum(success_count) AS success_count,
    sum(error_count) AS error_count,
    round((((sum(error_count))::numeric / (NULLIF(sum(total_requests), 0))::numeric) * (100)::numeric), 2) AS error_rate_pct,
    round(avg(avg_response_ms)) AS avg_response_ms,
    max(p95_response_ms) AS p95_response_ms,
    sum(unique_clients) AS unique_clients
   FROM analytics.api_usage
  WHERE ((year)::numeric = EXTRACT(year FROM now()))
  GROUP BY endpoint
  ORDER BY (sum(total_requests)) DESC;


ALTER VIEW public.v_api_performance OWNER TO postgres;

--
-- Name: v_app_mode_usage; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_app_mode_usage AS
 SELECT platform,
    lang,
    sum(scan_sessions) AS scan_sessions,
    sum(search_sessions) AS search_sessions,
    sum(chat_sessions) AS chat_sessions,
    sum(total_scans) AS total_scans,
    sum(total_searches) AS total_searches,
    sum(total_chats) AS total_chats,
    sum(zero_result_searches) AS zero_result_searches,
    round(avg(scan_to_save_rate), 2) AS avg_scan_to_save_rate,
    round(avg(search_to_save_rate), 2) AS avg_search_to_save_rate,
    round(avg(chat_to_save_rate), 2) AS avg_chat_to_save_rate
   FROM analytics.app_behaviour
  GROUP BY platform, lang
  ORDER BY (sum(total_scans)) DESC;


ALTER VIEW public.v_app_mode_usage OWNER TO postgres;

--
-- Name: v_basket_prices; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_basket_prices AS
 SELECT pp.gtin,
    pp.store,
    pr.name_en AS product_name,
    pr.category,
    pr.ontology_tags,
    pp.price_chf,
    pp.price_per_100g,
    pp.is_promotion,
    pp.discount_pct,
    pp.price_date
   FROM (public.product_prices pp
     JOIN public.products pr ON ((pr.id = pp.product_id)))
  WHERE ((pp.price_date = ( SELECT max(pp2.price_date) AS max
           FROM public.product_prices pp2
          WHERE (pp2.product_id = pp.product_id))) AND (pr.is_active = true));


ALTER VIEW public.v_basket_prices OWNER TO postgres;

--
-- Name: VIEW v_basket_prices; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_basket_prices IS 'Used by basket calculator. Join with user list items on GTIN.
     Filter ontology_tags for dietary compliance.
     GROUP BY store to get per-store basket totals.';


--
-- Name: v_best_value; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_best_value AS
 SELECT pp.gtin,
    pp.store,
    pr.name_en AS product_name,
    pr.brand,
    pr.category,
    pr.pack_size_raw,
    pr.unit_quantity,
    pr.unit_type,
    pp.price_chf,
    pp.price_per_100g,
    pp.price_per_pack_unit,
    pp.is_promotion,
    pp.discount_pct,
    rank() OVER (PARTITION BY pp.gtin ORDER BY pp.price_per_100g) AS value_rank,
        CASE
            WHEN pp.is_promotion THEN 'on_sale'::text
            WHEN (rank() OVER (PARTITION BY pp.gtin ORDER BY pp.price_per_100g) = 1) THEN 'best_value'::text
            ELSE 'standard'::text
        END AS value_badge
   FROM (public.product_prices pp
     JOIN public.products pr ON ((pr.id = pp.product_id)))
  WHERE (pp.price_date = ( SELECT max(pp2.price_date) AS max
           FROM public.product_prices pp2
          WHERE (pp2.product_id = pp.product_id)));


ALTER VIEW public.v_best_value OWNER TO postgres;

--
-- Name: VIEW v_best_value; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_best_value IS 'Ranks stores by price per 100g for each product. Powers best-value badge.';


--
-- Name: v_disputed_verdicts; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_disputed_verdicts AS
 SELECT verdict_key,
    store,
    sum(dispute_count) AS total_disputes,
    sum(resolved_count) AS resolved_count,
    sum(
        CASE
            WHEN ontology_updated THEN 1
            ELSE 0
        END) AS ontology_fixes,
    round((((sum(resolved_count))::numeric / (NULLIF(sum(dispute_count), 0))::numeric) * (100)::numeric), 1) AS resolution_rate_pct
   FROM analytics.verdict_disputes
  GROUP BY verdict_key, store
  ORDER BY (sum(dispute_count)) DESC;


ALTER VIEW public.v_disputed_verdicts OWNER TO postgres;

--
-- Name: v_error_health; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_error_health AS
 SELECT error_type,
    endpoint,
    count(*) AS occurrences,
    count(DISTINCT session_id) AS sessions_affected,
    min(created_at) AS first_seen,
    max(created_at) AS last_seen,
    round(((count(*))::numeric / NULLIF((EXTRACT(epoch FROM (max(created_at) - min(created_at))) / (3600)::numeric), (0)::numeric)), 2) AS errors_per_hour
   FROM events.error_events
  WHERE (created_at >= (now() - '7 days'::interval))
  GROUP BY error_type, endpoint
  ORDER BY (count(*)) DESC;


ALTER VIEW public.v_error_health OWNER TO postgres;

--
-- Name: v_feature_popularity; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_feature_popularity AS
 SELECT feature,
    platform,
    sum(usage_count) AS total_usage,
    sum(unique_users) AS total_users,
    round(avg(avg_duration_ms)) AS avg_duration_ms,
    round(((sum(usage_count))::numeric / (NULLIF(sum(unique_users), 0))::numeric), 2) AS uses_per_user
   FROM analytics.feature_popularity
  GROUP BY feature, platform
  ORDER BY (sum(usage_count)) DESC;


ALTER VIEW public.v_feature_popularity OWNER TO postgres;

--
-- Name: v_llm_quality; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_llm_quality AS
 SELECT detected_intent,
    lang,
    sum(total_interactions) AS total_interactions,
    round(avg(avg_response_ms)) AS avg_response_ms,
    round(avg(avg_products_returned), 1) AS avg_products_returned,
    sum(saves_from_chat) AS saves_from_chat,
    sum(follow_up_count) AS follow_ups,
    sum(zero_product_returns) AS zero_result_responses,
    round((((sum(saves_from_chat))::numeric / (NULLIF(sum(total_interactions), 0))::numeric) * (100)::numeric), 1) AS save_conversion_pct,
    round(avg(avg_tokens_in)) AS avg_tokens_in,
    round(avg(avg_tokens_out)) AS avg_tokens_out
   FROM analytics.llm_quality
  GROUP BY detected_intent, lang
  ORDER BY (sum(total_interactions)) DESC;


ALTER VIEW public.v_llm_quality OWNER TO postgres;

--
-- Name: v_ontology_priority; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_ontology_priority AS
 SELECT ontology_group,
    lang,
    count(*) AS pending_count,
    sum(
        CASE
            WHEN (priority = 1) THEN 1
            ELSE 0
        END) AS urgent,
    sum(
        CASE
            WHEN (priority = 2) THEN 1
            ELSE 0
        END) AS high,
    sum(
        CASE
            WHEN (priority = 3) THEN 1
            ELSE 0
        END) AS medium,
    max(created_at) AS latest
   FROM etl.ontology_improvement_queue
  WHERE (status = 'pending'::text)
  GROUP BY ontology_group, lang
  ORDER BY (sum(
        CASE
            WHEN (priority = 1) THEN 1
            ELSE 0
        END)) DESC, (count(*)) DESC;


ALTER VIEW public.v_ontology_priority OWNER TO postgres;

--
-- Name: VIEW v_ontology_priority; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_ontology_priority IS 'Pending ontology improvements ranked by urgency. Used by staff dashboard.';


--
-- Name: v_price_comparison; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_price_comparison AS
 SELECT p.canonical_gtin AS gtin,
    p.canonical_name_en AS product_name,
    p.canonical_brand AS brand,
    p.canonical_category AS category,
    s.snapshot_date,
    s.prices_chf,
    s.prices_per_100g,
    s.cheapest_store,
    s.cheapest_price AS cheapest_price_chf,
    s.most_expensive_store,
    s.most_expensive_price AS most_expensive_price_chf,
    s.price_spread_chf,
    s.price_spread_pct,
    s.stores_compared
   FROM (public.unified_products p
     JOIN public.store_price_snapshot s ON (((s.gtin)::text = (p.canonical_gtin)::text)))
  WHERE (s.snapshot_date = ( SELECT max(s2.snapshot_date) AS max
           FROM public.store_price_snapshot s2
          WHERE ((s2.gtin)::text = (p.canonical_gtin)::text)));


ALTER VIEW public.v_price_comparison OWNER TO postgres;

--
-- Name: VIEW v_price_comparison; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_price_comparison IS 'Live cross-store price comparison. One row per product. Updated daily.';


--
-- Name: v_price_history_stats; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_price_history_stats AS
 SELECT gtin,
    store,
    price_date,
    price_chf,
    price_per_100g,
    is_promotion,
    round(avg(price_chf) OVER (PARTITION BY gtin, store ORDER BY price_date ROWS BETWEEN 27 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_28d,
    lag(price_chf, 30) OVER (PARTITION BY gtin, store ORDER BY price_date) AS price_30d_ago,
        CASE
            WHEN (price_chf < lag(price_chf, 1) OVER (PARTITION BY gtin, store ORDER BY price_date)) THEN 'down'::text
            WHEN (price_chf > lag(price_chf, 1) OVER (PARTITION BY gtin, store ORDER BY price_date)) THEN 'up'::text
            ELSE 'stable'::text
        END AS price_direction,
    min(price_chf) OVER (PARTITION BY gtin, store) AS all_time_low,
    max(price_chf) OVER (PARTITION BY gtin, store) AS all_time_high
   FROM public.price_history ph;


ALTER VIEW public.v_price_history_stats OWNER TO postgres;

--
-- Name: VIEW v_price_history_stats; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_price_history_stats IS 'Price history enriched with rolling averages, direction, and all-time stats.';


--
-- Name: v_price_intelligence; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_price_intelligence AS
 SELECT gtin,
    store,
    product_name,
    category,
    avg_price_chf,
    min_price_chf,
    max_price_chf,
    promotion_days,
    round((max_price_chf - min_price_chf), 2) AS price_range_chf,
    round((((max_price_chf - min_price_chf) / NULLIF(min_price_chf, (0)::numeric)) * (100)::numeric), 1) AS price_volatility_pct
   FROM analytics.price_analytics pa
  WHERE ((year)::numeric = EXTRACT(year FROM now()))
  ORDER BY gtin, store, week_number DESC;


ALTER VIEW public.v_price_intelligence OWNER TO postgres;

--
-- Name: v_product_popularity; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_product_popularity AS
 SELECT gtin,
    store,
    product_name,
    category,
    sum(total_scans) AS total_scans,
    sum(total_saves) AS total_saves,
    sum(total_searches) AS total_searches,
    sum(total_views) AS total_views,
    sum(total_feedback) AS total_feedback,
    sum(positive_feedback) AS positive_feedback,
    sum(negative_feedback) AS negative_feedback,
        CASE
            WHEN (sum(total_feedback) > 0) THEN round((((sum(positive_feedback))::numeric / (sum(total_feedback))::numeric) * (100)::numeric), 1)
            ELSE NULL::numeric
        END AS positive_feedback_pct,
    sum(((total_scans + total_saves) + total_searches)) AS engagement_score
   FROM analytics.product_performance
  GROUP BY gtin, store, product_name, category
  ORDER BY (sum(((total_scans + total_saves) + total_searches))) DESC;


ALTER VIEW public.v_product_popularity OWNER TO postgres;

--
-- Name: v_scraper_health; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_scraper_health AS
 SELECT s.store,
    s.scrape_type,
    s.is_active,
    s.last_success_at,
    s.last_attempt_at,
    s.consecutive_failures,
    s.rate_limit_rps,
    (EXTRACT(epoch FROM (now() - s.last_success_at)) / (3600)::numeric) AS hours_since_success,
    j.status AS last_job_status,
    j.products_created AS last_products_created,
    j.prices_updated AS last_prices_updated,
    j.failures_count AS last_failures,
    j.finished_at AS last_job_finished
   FROM (etl.scraper_sources s
     LEFT JOIN LATERAL ( SELECT scraper_jobs.status,
            scraper_jobs.products_created,
            scraper_jobs.prices_updated,
            scraper_jobs.failures_count,
            scraper_jobs.finished_at
           FROM etl.scraper_jobs
          WHERE ((scraper_jobs.store)::text = (s.store)::text)
          ORDER BY scraper_jobs.queued_at DESC
         LIMIT 1) j ON (true))
  ORDER BY s.consecutive_failures DESC, s.last_success_at;


ALTER VIEW public.v_scraper_health OWNER TO postgres;

--
-- Name: VIEW v_scraper_health; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_scraper_health IS 'Live scraper status per store. Shows staleness and last job outcome.';


--
-- Name: v_session_quality; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_session_quality AS
 SELECT platform,
    lang,
    sum(total_sessions) AS total_sessions,
    round(avg(avg_duration_secs)) AS avg_duration_secs,
    round(avg(avg_events_per_session), 1) AS avg_events,
    sum(bounce_count) AS total_bounces,
    round((((sum(bounce_count))::numeric / (NULLIF(sum(total_sessions), 0))::numeric) * (100)::numeric), 1) AS bounce_rate_pct,
    sum(found_product_count) AS found_product_count,
    round((((sum(found_product_count))::numeric / (NULLIF(sum(total_sessions), 0))::numeric) * (100)::numeric), 1) AS success_rate_pct
   FROM analytics.session_quality
  GROUP BY platform, lang
  ORDER BY (sum(total_sessions)) DESC;


ALTER VIEW public.v_session_quality OWNER TO postgres;

--
-- Name: v_swiss_dietary_demand; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_swiss_dietary_demand AS
 SELECT region,
    dietary_type,
    sum(scan_count) AS total_scans,
    sum(search_count) AS total_searches,
    sum((scan_count + search_count)) AS total_demand,
    max(updated_at) AS last_updated
   FROM analytics.swiss_regional
  GROUP BY region, dietary_type
  ORDER BY (sum((scan_count + search_count))) DESC;


ALTER VIEW public.v_swiss_dietary_demand OWNER TO postgres;

--
-- Name: v_user_growth; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_user_growth AS
 SELECT week_start,
    year,
    week_number,
    new_users,
    logins,
    active_users,
    scan_users,
    search_users,
    chat_users,
    round(((((new_users)::numeric / (NULLIF(lag(new_users) OVER (ORDER BY year, week_number), 0))::numeric) * (100)::numeric) - (100)::numeric), 1) AS new_user_growth_pct
   FROM analytics.user_growth
  ORDER BY year DESC, week_number DESC;


ALTER VIEW public.v_user_growth OWNER TO postgres;

--
-- Name: verdict_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.verdict_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    verdict_key text NOT NULL,
    store text,
    category text,
    lang character(2),
    request_count integer DEFAULT 0,
    positive_count integer DEFAULT 0,
    negative_count integer DEFAULT 0,
    feedback_count integer DEFAULT 0,
    week_number integer,
    month_number integer,
    year integer,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.verdict_analytics OWNER TO postgres;

--
-- Name: allergen_risk allergen_risk_allergen_type_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.allergen_risk
    ADD CONSTRAINT allergen_risk_allergen_type_year_month_number_key UNIQUE (allergen_type, year, month_number);


--
-- Name: allergen_risk allergen_risk_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.allergen_risk
    ADD CONSTRAINT allergen_risk_pkey PRIMARY KEY (id);


--
-- Name: api_usage api_usage_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.api_usage
    ADD CONSTRAINT api_usage_pkey PRIMARY KEY (id);


--
-- Name: api_usage api_usage_year_week_number_endpoint_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.api_usage
    ADD CONSTRAINT api_usage_year_week_number_endpoint_key UNIQUE (year, week_number, endpoint);


--
-- Name: app_behaviour app_behaviour_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.app_behaviour
    ADD CONSTRAINT app_behaviour_pkey PRIMARY KEY (id);


--
-- Name: app_behaviour app_behaviour_year_week_number_platform_lang_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.app_behaviour
    ADD CONSTRAINT app_behaviour_year_week_number_platform_lang_key UNIQUE (year, week_number, platform, lang);


--
-- Name: b2b_report_access b2b_report_access_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.b2b_report_access
    ADD CONSTRAINT b2b_report_access_pkey PRIMARY KEY (id);


--
-- Name: category_analytics category_analytics_category_store_lang_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.category_analytics
    ADD CONSTRAINT category_analytics_category_store_lang_year_month_number_key UNIQUE (category, store, lang, year, month_number);


--
-- Name: category_analytics category_analytics_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.category_analytics
    ADD CONSTRAINT category_analytics_pkey PRIMARY KEY (id);


--
-- Name: dietary_trends dietary_trends_dietary_type_region_lang_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.dietary_trends
    ADD CONSTRAINT dietary_trends_dietary_type_region_lang_year_month_number_key UNIQUE (dietary_type, region, lang, year, month_number);


--
-- Name: dietary_trends dietary_trends_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.dietary_trends
    ADD CONSTRAINT dietary_trends_pkey PRIMARY KEY (id);


--
-- Name: feature_popularity feature_popularity_feature_platform_lang_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.feature_popularity
    ADD CONSTRAINT feature_popularity_feature_platform_lang_year_month_number_key UNIQUE (feature, platform, lang, year, month_number);


--
-- Name: feature_popularity feature_popularity_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.feature_popularity
    ADD CONSTRAINT feature_popularity_pkey PRIMARY KEY (id);


--
-- Name: llm_quality llm_quality_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.llm_quality
    ADD CONSTRAINT llm_quality_pkey PRIMARY KEY (id);


--
-- Name: llm_quality llm_quality_year_week_number_lang_detected_intent_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.llm_quality
    ADD CONSTRAINT llm_quality_year_week_number_lang_detected_intent_key UNIQUE (year, week_number, lang, detected_intent);


--
-- Name: price_analytics price_analytics_gtin_store_year_week_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.price_analytics
    ADD CONSTRAINT price_analytics_gtin_store_year_week_number_key UNIQUE (gtin, store, year, week_number);


--
-- Name: price_analytics price_analytics_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.price_analytics
    ADD CONSTRAINT price_analytics_pkey PRIMARY KEY (id);


--
-- Name: product_performance product_performance_gtin_store_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.product_performance
    ADD CONSTRAINT product_performance_gtin_store_year_month_number_key UNIQUE (gtin, store, year, month_number);


--
-- Name: product_performance product_performance_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.product_performance
    ADD CONSTRAINT product_performance_pkey PRIMARY KEY (id);


--
-- Name: rebuild_log rebuild_log_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.rebuild_log
    ADD CONSTRAINT rebuild_log_pkey PRIMARY KEY (id);


--
-- Name: retention_cohorts retention_cohorts_cohort_year_cohort_week_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.retention_cohorts
    ADD CONSTRAINT retention_cohorts_cohort_year_cohort_week_key UNIQUE (cohort_year, cohort_week);


--
-- Name: retention_cohorts retention_cohorts_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.retention_cohorts
    ADD CONSTRAINT retention_cohorts_pkey PRIMARY KEY (id);


--
-- Name: search_patterns search_patterns_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.search_patterns
    ADD CONSTRAINT search_patterns_pkey PRIMARY KEY (id);


--
-- Name: search_patterns search_patterns_year_week_number_lang_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.search_patterns
    ADD CONSTRAINT search_patterns_year_week_number_lang_key UNIQUE (year, week_number, lang);


--
-- Name: session_quality session_quality_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.session_quality
    ADD CONSTRAINT session_quality_pkey PRIMARY KEY (id);


--
-- Name: session_quality session_quality_year_week_number_platform_lang_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.session_quality
    ADD CONSTRAINT session_quality_year_week_number_platform_lang_key UNIQUE (year, week_number, platform, lang);


--
-- Name: swiss_regional swiss_regional_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.swiss_regional
    ADD CONSTRAINT swiss_regional_pkey PRIMARY KEY (id);


--
-- Name: swiss_regional swiss_regional_region_lang_dietary_type_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.swiss_regional
    ADD CONSTRAINT swiss_regional_region_lang_dietary_type_year_month_number_key UNIQUE (region, lang, dietary_type, year, month_number);


--
-- Name: user_growth user_growth_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.user_growth
    ADD CONSTRAINT user_growth_pkey PRIMARY KEY (id);


--
-- Name: user_growth user_growth_year_week_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.user_growth
    ADD CONSTRAINT user_growth_year_week_number_key UNIQUE (year, week_number);


--
-- Name: verdict_analytics verdict_analytics_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.verdict_analytics
    ADD CONSTRAINT verdict_analytics_pkey PRIMARY KEY (id);


--
-- Name: verdict_analytics verdict_analytics_verdict_key_store_lang_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.verdict_analytics
    ADD CONSTRAINT verdict_analytics_verdict_key_store_lang_year_month_number_key UNIQUE (verdict_key, store, lang, year, month_number);


--
-- Name: verdict_disputes verdict_disputes_gtin_store_verdict_key_year_month_number_key; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.verdict_disputes
    ADD CONSTRAINT verdict_disputes_gtin_store_verdict_key_year_month_number_key UNIQUE (gtin, store, verdict_key, year, month_number);


--
-- Name: verdict_disputes verdict_disputes_pkey; Type: CONSTRAINT; Schema: analytics; Owner: postgres
--

ALTER TABLE ONLY analytics.verdict_disputes
    ADD CONSTRAINT verdict_disputes_pkey PRIMARY KEY (id);


--
-- Name: ontology_improvement_queue ontology_improvement_queue_pkey; Type: CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.ontology_improvement_queue
    ADD CONSTRAINT ontology_improvement_queue_pkey PRIMARY KEY (id);


--
-- Name: scrape_failures scrape_failures_pkey; Type: CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scrape_failures
    ADD CONSTRAINT scrape_failures_pkey PRIMARY KEY (id);


--
-- Name: scraper_change_log scraper_change_log_pkey; Type: CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scraper_change_log
    ADD CONSTRAINT scraper_change_log_pkey PRIMARY KEY (id);


--
-- Name: scraper_jobs scraper_jobs_pkey; Type: CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scraper_jobs
    ADD CONSTRAINT scraper_jobs_pkey PRIMARY KEY (id);


--
-- Name: scraper_sources scraper_sources_pkey; Type: CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scraper_sources
    ADD CONSTRAINT scraper_sources_pkey PRIMARY KEY (id);


--
-- Name: scraper_sources scraper_sources_store_key; Type: CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scraper_sources
    ADD CONSTRAINT scraper_sources_store_key UNIQUE (store);


--
-- Name: staging_products staging_products_pkey; Type: CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.staging_products
    ADD CONSTRAINT staging_products_pkey PRIMARY KEY (id);


--
-- Name: allergen_alert_events allergen_alert_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.allergen_alert_events
    ADD CONSTRAINT allergen_alert_events_pkey PRIMARY KEY (id);


--
-- Name: api_events api_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.api_events
    ADD CONSTRAINT api_events_pkey PRIMARY KEY (id);


--
-- Name: chat_events chat_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.chat_events
    ADD CONSTRAINT chat_events_pkey PRIMARY KEY (id);


--
-- Name: error_events error_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.error_events
    ADD CONSTRAINT error_events_pkey PRIMARY KEY (id);


--
-- Name: feature_events feature_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.feature_events
    ADD CONSTRAINT feature_events_pkey PRIMARY KEY (id);


--
-- Name: feedback_events feedback_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.feedback_events
    ADD CONSTRAINT feedback_events_pkey PRIMARY KEY (id);


--
-- Name: price_events price_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.price_events
    ADD CONSTRAINT price_events_pkey PRIMARY KEY (id);


--
-- Name: product_events product_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.product_events
    ADD CONSTRAINT product_events_pkey PRIMARY KEY (id);


--
-- Name: scan_events scan_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.scan_events
    ADD CONSTRAINT scan_events_pkey PRIMARY KEY (id);


--
-- Name: search_events search_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.search_events
    ADD CONSTRAINT search_events_pkey PRIMARY KEY (id);


--
-- Name: session_events session_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.session_events
    ADD CONSTRAINT session_events_pkey PRIMARY KEY (id);


--
-- Name: user_events user_events_pkey; Type: CONSTRAINT; Schema: events; Owner: postgres
--

ALTER TABLE ONLY events.user_events
    ADD CONSTRAINT user_events_pkey PRIMARY KEY (id);


--
-- Name: agent_execution_log agent_execution_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_execution_log
    ADD CONSTRAINT agent_execution_log_pkey PRIMARY KEY (id);


--
-- Name: allergen_alert_analytics allergen_alert_analytics_gtin_store_allergen_type_year_mont_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.allergen_alert_analytics
    ADD CONSTRAINT allergen_alert_analytics_gtin_store_allergen_type_year_mont_key UNIQUE (gtin, store, allergen_type, year, month_number);


--
-- Name: allergen_alert_analytics allergen_alert_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.allergen_alert_analytics
    ADD CONSTRAINT allergen_alert_analytics_pkey PRIMARY KEY (id);


--
-- Name: api_usage_analytics api_usage_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage_analytics
    ADD CONSTRAINT api_usage_analytics_pkey PRIMARY KEY (id);


--
-- Name: app_behaviour_analytics app_behaviour_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.app_behaviour_analytics
    ADD CONSTRAINT app_behaviour_analytics_pkey PRIMARY KEY (id);


--
-- Name: b2b_report_access_log b2b_report_access_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.b2b_report_access_log
    ADD CONSTRAINT b2b_report_access_log_pkey PRIMARY KEY (id);


--
-- Name: barcode_aliases barcode_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.barcode_aliases
    ADD CONSTRAINT barcode_aliases_pkey PRIMARY KEY (id);


--
-- Name: category_analytics category_analytics_category_store_lang_year_month_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.category_analytics
    ADD CONSTRAINT category_analytics_category_store_lang_year_month_number_key UNIQUE (category, store, lang, year, month_number);


--
-- Name: category_analytics category_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.category_analytics
    ADD CONSTRAINT category_analytics_pkey PRIMARY KEY (id);


--
-- Name: consent_audit_log consent_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consent_audit_log
    ADD CONSTRAINT consent_audit_log_pkey PRIMARY KEY (id);


--
-- Name: data_access_log data_access_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.data_access_log
    ADD CONSTRAINT data_access_log_pkey PRIMARY KEY (id);


--
-- Name: data_deletion_log data_deletion_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.data_deletion_log
    ADD CONSTRAINT data_deletion_log_pkey PRIMARY KEY (id);


--
-- Name: dietary_trend_analytics dietary_trend_analytics_dietary_type_region_lang_year_month_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dietary_trend_analytics
    ADD CONSTRAINT dietary_trend_analytics_dietary_type_region_lang_year_month_key UNIQUE (dietary_type, region, lang, year, month_number);


--
-- Name: dietary_trend_analytics dietary_trend_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dietary_trend_analytics
    ADD CONSTRAINT dietary_trend_analytics_pkey PRIMARY KEY (id);


--
-- Name: error_analytics error_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_analytics
    ADD CONSTRAINT error_analytics_pkey PRIMARY KEY (id);


--
-- Name: feature_usage_analytics feature_usage_analytics_feature_platform_lang_year_month_nu_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feature_usage_analytics
    ADD CONSTRAINT feature_usage_analytics_feature_platform_lang_year_month_nu_key UNIQUE (feature, platform, lang, year, month_number);


--
-- Name: feature_usage_analytics feature_usage_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feature_usage_analytics
    ADD CONSTRAINT feature_usage_analytics_pkey PRIMARY KEY (id);


--
-- Name: llm_interaction_analytics llm_interaction_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.llm_interaction_analytics
    ADD CONSTRAINT llm_interaction_analytics_pkey PRIMARY KEY (id);


--
-- Name: nutrition_facts nutrition_facts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nutrition_facts
    ADD CONSTRAINT nutrition_facts_pkey PRIMARY KEY (id);


--
-- Name: nutrition_facts nutrition_facts_product_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nutrition_facts
    ADD CONSTRAINT nutrition_facts_product_id_key UNIQUE (product_id);


--
-- Name: ontology_current ontology_current_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_current
    ADD CONSTRAINT ontology_current_pkey PRIMARY KEY (lock);


--
-- Name: ontology_improvement_queue ontology_improvement_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_improvement_queue
    ADD CONSTRAINT ontology_improvement_queue_pkey PRIMARY KEY (id);


--
-- Name: ontology_versions ontology_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_versions
    ADD CONSTRAINT ontology_versions_pkey PRIMARY KEY (version);


--
-- Name: price_analytics price_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.price_analytics
    ADD CONSTRAINT price_analytics_pkey PRIMARY KEY (id);


--
-- Name: price_history price_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.price_history
    ADD CONSTRAINT price_history_pkey PRIMARY KEY (id);


--
-- Name: privacy_policy_versions privacy_policy_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.privacy_policy_versions
    ADD CONSTRAINT privacy_policy_versions_pkey PRIMARY KEY (version);


--
-- Name: product_analytics product_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_analytics
    ADD CONSTRAINT product_analytics_pkey PRIMARY KEY (id);


--
-- Name: product_performance product_performance_gtin_store_year_month_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_performance
    ADD CONSTRAINT product_performance_gtin_store_year_month_number_key UNIQUE (gtin, store, year, month_number);


--
-- Name: product_performance product_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_performance
    ADD CONSTRAINT product_performance_pkey PRIMARY KEY (id);


--
-- Name: product_prices product_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_prices
    ADD CONSTRAINT product_prices_pkey PRIMARY KEY (id);


--
-- Name: product_prices product_prices_product_id_store_price_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_prices
    ADD CONSTRAINT product_prices_product_id_store_price_date_key UNIQUE (product_id, store, price_date);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: retention_analytics retention_analytics_cohort_year_cohort_week_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.retention_analytics
    ADD CONSTRAINT retention_analytics_cohort_year_cohort_week_key UNIQUE (cohort_year, cohort_week);


--
-- Name: retention_analytics retention_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.retention_analytics
    ADD CONSTRAINT retention_analytics_pkey PRIMARY KEY (id);


--
-- Name: search_analytics search_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.search_analytics
    ADD CONSTRAINT search_analytics_pkey PRIMARY KEY (id);


--
-- Name: session_analytics session_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_analytics
    ADD CONSTRAINT session_analytics_pkey PRIMARY KEY (id);


--
-- Name: session_analytics session_analytics_session_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_analytics
    ADD CONSTRAINT session_analytics_session_id_key UNIQUE (session_id);


--
-- Name: store_comparison_analytics store_comparison_analytics_gtin_comparison_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.store_comparison_analytics
    ADD CONSTRAINT store_comparison_analytics_gtin_comparison_date_key UNIQUE (gtin, comparison_date);


--
-- Name: store_comparison_analytics store_comparison_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.store_comparison_analytics
    ADD CONSTRAINT store_comparison_analytics_pkey PRIMARY KEY (id);


--
-- Name: store_price_snapshot store_price_snapshot_gtin_snapshot_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.store_price_snapshot
    ADD CONSTRAINT store_price_snapshot_gtin_snapshot_date_key UNIQUE (gtin, snapshot_date);


--
-- Name: store_price_snapshot store_price_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.store_price_snapshot
    ADD CONSTRAINT store_price_snapshot_pkey PRIMARY KEY (id);


--
-- Name: swiss_regional_analytics swiss_regional_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.swiss_regional_analytics
    ADD CONSTRAINT swiss_regional_analytics_pkey PRIMARY KEY (id);


--
-- Name: swiss_regional_analytics swiss_regional_analytics_region_lang_dietary_type_year_mont_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.swiss_regional_analytics
    ADD CONSTRAINT swiss_regional_analytics_region_lang_dietary_type_year_mont_key UNIQUE (region, lang, dietary_type, year, month_number);


--
-- Name: unified_product_members unified_product_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unified_product_members
    ADD CONSTRAINT unified_product_members_pkey PRIMARY KEY (unified_id, product_id);


--
-- Name: unified_products unified_products_canonical_gtin_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unified_products
    ADD CONSTRAINT unified_products_canonical_gtin_key UNIQUE (canonical_gtin);


--
-- Name: unified_products unified_products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unified_products
    ADD CONSTRAINT unified_products_pkey PRIMARY KEY (unified_id);


--
-- Name: products unique_product_store; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT unique_product_store UNIQUE (gtin, store);


--
-- Name: user_analytics user_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_analytics
    ADD CONSTRAINT user_analytics_pkey PRIMARY KEY (id);


--
-- Name: user_chat_history user_chat_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_chat_history
    ADD CONSTRAINT user_chat_history_pkey PRIMARY KEY (id);


--
-- Name: user_feedback user_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_pkey PRIMARY KEY (id);


--
-- Name: user_list_items user_list_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_list_items
    ADD CONSTRAINT user_list_items_pkey PRIMARY KEY (id);


--
-- Name: user_lists user_lists_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_lists
    ADD CONSTRAINT user_lists_pkey PRIMARY KEY (id);


--
-- Name: user_preferences user_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_preferences
    ADD CONSTRAINT user_preferences_pkey PRIMARY KEY (id);


--
-- Name: user_preferences user_preferences_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_preferences
    ADD CONSTRAINT user_preferences_user_id_key UNIQUE (user_id);


--
-- Name: user_saved_products user_saved_products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_saved_products
    ADD CONSTRAINT user_saved_products_pkey PRIMARY KEY (id);


--
-- Name: user_scans user_scans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_scans
    ADD CONSTRAINT user_scans_pkey PRIMARY KEY (id);


--
-- Name: user_searches user_searches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_searches
    ADD CONSTRAINT user_searches_pkey PRIMARY KEY (id);


--
-- Name: verdict_analytics verdict_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verdict_analytics
    ADD CONSTRAINT verdict_analytics_pkey PRIMARY KEY (id);


--
-- Name: verdict_analytics verdict_analytics_verdict_key_store_lang_year_month_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verdict_analytics
    ADD CONSTRAINT verdict_analytics_verdict_key_store_lang_year_month_number_key UNIQUE (verdict_key, store, lang, year, month_number);


--
-- Name: verdict_dispute_analytics verdict_dispute_analytics_gtin_store_verdict_key_year_month_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verdict_dispute_analytics
    ADD CONSTRAINT verdict_dispute_analytics_gtin_store_verdict_key_year_month_key UNIQUE (gtin, store, verdict_key, year, month_number);


--
-- Name: verdict_dispute_analytics verdict_dispute_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verdict_dispute_analytics
    ADD CONSTRAINT verdict_dispute_analytics_pkey PRIMARY KEY (id);


--
-- Name: idx_an_b2b_client; Type: INDEX; Schema: analytics; Owner: postgres
--

CREATE INDEX idx_an_b2b_client ON analytics.b2b_report_access USING btree (client_name, accessed_at DESC);


--
-- Name: idx_an_product_perf_category; Type: INDEX; Schema: analytics; Owner: postgres
--

CREATE INDEX idx_an_product_perf_category ON analytics.product_performance USING btree (category, total_scans DESC);


--
-- Name: idx_an_product_perf_gtin; Type: INDEX; Schema: analytics; Owner: postgres
--

CREATE INDEX idx_an_product_perf_gtin ON analytics.product_performance USING btree (gtin, store);


--
-- Name: idx_rebuild_log_job; Type: INDEX; Schema: analytics; Owner: postgres
--

CREATE INDEX idx_rebuild_log_job ON analytics.rebuild_log USING btree (job_name, started_at DESC);


--
-- Name: idx_change_log_gtin; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_change_log_gtin ON etl.scraper_change_log USING btree (gtin, store, changed_at DESC);


--
-- Name: idx_change_log_job; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_change_log_job ON etl.scraper_change_log USING btree (job_id);


--
-- Name: idx_change_log_type; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_change_log_type ON etl.scraper_change_log USING btree (change_type, changed_at DESC);


--
-- Name: idx_failures_store; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_failures_store ON etl.scrape_failures USING btree (store, occurred_at DESC);


--
-- Name: idx_failures_unresolved; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_failures_unresolved ON etl.scrape_failures USING btree (is_resolved, store) WHERE (is_resolved = false);


--
-- Name: idx_jobs_status; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_jobs_status ON etl.scraper_jobs USING btree (status, queued_at DESC);


--
-- Name: idx_jobs_store_status; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_jobs_store_status ON etl.scraper_jobs USING btree (store, status, queued_at DESC);


--
-- Name: idx_ont_queue_group; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_ont_queue_group ON etl.ontology_improvement_queue USING btree (ontology_group, status);


--
-- Name: idx_ont_queue_status; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_ont_queue_status ON etl.ontology_improvement_queue USING btree (status, priority DESC);


--
-- Name: idx_staging_gtin; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_staging_gtin ON etl.staging_products USING btree (gtin, store);


--
-- Name: idx_staging_job_status; Type: INDEX; Schema: etl; Owner: postgres
--

CREATE INDEX idx_staging_job_status ON etl.staging_products USING btree (job_id, status);


--
-- Name: idx_ev_allergen_gtin; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_allergen_gtin ON events.allergen_alert_events USING btree (gtin, store);


--
-- Name: idx_ev_allergen_type; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_allergen_type ON events.allergen_alert_events USING btree (allergen_type, created_at DESC);


--
-- Name: idx_ev_allergen_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_allergen_user ON events.allergen_alert_events USING btree (user_id, created_at DESC) WHERE (user_has_allergy = true);


--
-- Name: idx_ev_api_client; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_api_client ON events.api_events USING btree (api_key_hash, created_at DESC);


--
-- Name: idx_ev_api_endpoint; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_api_endpoint ON events.api_events USING btree (endpoint, created_at DESC);


--
-- Name: idx_ev_api_errors; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_api_errors ON events.api_events USING btree (status_code, created_at DESC) WHERE (status_code >= 400);


--
-- Name: idx_ev_chat_dietary; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_chat_dietary ON events.chat_events USING btree (detected_dietary, created_at DESC);


--
-- Name: idx_ev_chat_intent; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_chat_intent ON events.chat_events USING btree (detected_intent, created_at DESC);


--
-- Name: idx_ev_chat_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_chat_user ON events.chat_events USING btree (user_id, created_at DESC);


--
-- Name: idx_ev_error_endpoint; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_error_endpoint ON events.error_events USING btree (endpoint, created_at DESC);


--
-- Name: idx_ev_error_type; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_error_type ON events.error_events USING btree (error_type, created_at DESC);


--
-- Name: idx_ev_feature_type; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_feature_type ON events.feature_events USING btree (feature, created_at DESC);


--
-- Name: idx_ev_feature_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_feature_user ON events.feature_events USING btree (user_id, created_at DESC);


--
-- Name: idx_ev_feedback_disputes; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_feedback_disputes ON events.feedback_events USING btree (is_dispute, created_at DESC) WHERE (is_dispute = true);


--
-- Name: idx_ev_feedback_gtin; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_feedback_gtin ON events.feedback_events USING btree (gtin, verdict_key, created_at DESC);


--
-- Name: idx_ev_price_gtin; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_price_gtin ON events.price_events USING btree (gtin, store, created_at DESC);


--
-- Name: idx_ev_price_promotions; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_price_promotions ON events.price_events USING btree (event_type, price_date) WHERE (event_type = 'promotion_started'::text);


--
-- Name: idx_ev_price_type; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_price_type ON events.price_events USING btree (event_type, created_at DESC);


--
-- Name: idx_ev_product_gtin; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_product_gtin ON events.product_events USING btree (gtin, event_type, created_at DESC);


--
-- Name: idx_ev_product_type; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_product_type ON events.product_events USING btree (event_type, created_at DESC);


--
-- Name: idx_ev_product_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_product_user ON events.product_events USING btree (user_id, created_at DESC);


--
-- Name: idx_ev_scan_gtin; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_scan_gtin ON events.scan_events USING btree (gtin, created_at DESC);


--
-- Name: idx_ev_scan_store; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_scan_store ON events.scan_events USING btree (store, created_at DESC);


--
-- Name: idx_ev_scan_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_scan_user ON events.scan_events USING btree (user_id, created_at DESC);


--
-- Name: idx_ev_search_query; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_search_query ON events.search_events USING btree (query);


--
-- Name: idx_ev_search_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_search_user ON events.search_events USING btree (user_id, created_at DESC);


--
-- Name: idx_ev_search_zero; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_search_zero ON events.search_events USING btree (has_zero_results, created_at DESC) WHERE (has_zero_results = true);


--
-- Name: idx_ev_session_session; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_session_session ON events.session_events USING btree (session_id, created_at DESC);


--
-- Name: idx_ev_session_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_session_user ON events.session_events USING btree (user_id, created_at DESC);


--
-- Name: idx_ev_user_events_session; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_user_events_session ON events.user_events USING btree (session_id);


--
-- Name: idx_ev_user_events_type; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_user_events_type ON events.user_events USING btree (event_type, created_at DESC);


--
-- Name: idx_ev_user_events_user; Type: INDEX; Schema: events; Owner: postgres
--

CREATE INDEX idx_ev_user_events_user ON events.user_events USING btree (user_id, created_at DESC);


--
-- Name: idx_agent_log_input_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_log_input_type ON public.agent_execution_log USING btree (input_type, created_at DESC);


--
-- Name: idx_agent_log_intent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_log_intent ON public.agent_execution_log USING btree (intent_detected, created_at DESC);


--
-- Name: idx_agent_log_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_log_session ON public.agent_execution_log USING btree (session_id, created_at DESC);


--
-- Name: idx_agent_log_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_log_user ON public.agent_execution_log USING btree (user_id, created_at DESC);


--
-- Name: idx_allergen_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_allergen_gtin ON public.allergen_alert_analytics USING btree (gtin, store);


--
-- Name: idx_allergen_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_allergen_type ON public.allergen_alert_analytics USING btree (allergen_type, year, month_number);


--
-- Name: idx_analytics_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_category ON public.product_analytics USING btree (category, event_type);


--
-- Name: idx_analytics_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_gtin ON public.product_analytics USING btree (gtin, event_type);


--
-- Name: idx_analytics_store; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_store ON public.product_analytics USING btree (store, event_type);


--
-- Name: idx_analytics_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_time ON public.product_analytics USING btree (year, week_number, event_type);


--
-- Name: idx_analytics_verdict; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_verdict ON public.product_analytics USING btree (verdict_key);


--
-- Name: idx_api_endpoint; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_api_endpoint ON public.api_usage_analytics USING btree (endpoint, created_at DESC);


--
-- Name: idx_api_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_api_status ON public.api_usage_analytics USING btree (status_code, created_at DESC);


--
-- Name: idx_b2b_client; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_b2b_client ON public.b2b_report_access_log USING btree (client_name, accessed_at DESC);


--
-- Name: idx_barcode_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_barcode_gtin ON public.barcode_aliases USING btree (normalized_gtin);


--
-- Name: idx_barcode_raw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_barcode_raw ON public.barcode_aliases USING btree (raw_barcode);


--
-- Name: idx_barcode_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_barcode_unique ON public.barcode_aliases USING btree (raw_barcode, COALESCE(retailer, ''::text));


--
-- Name: idx_behaviour_platform; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_behaviour_platform ON public.app_behaviour_analytics USING btree (platform, created_at DESC);


--
-- Name: idx_behaviour_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_behaviour_time ON public.app_behaviour_analytics USING btree (year, month_number, week_number);


--
-- Name: idx_behaviour_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_behaviour_user ON public.app_behaviour_analytics USING btree (user_id, created_at DESC);


--
-- Name: idx_category_analytics; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_category_analytics ON public.category_analytics USING btree (category, year, month_number);


--
-- Name: idx_chat_history_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_session ON public.user_chat_history USING btree (session_id, created_at DESC);


--
-- Name: idx_chat_history_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_user ON public.user_chat_history USING btree (user_id, created_at DESC);


--
-- Name: idx_consent_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_consent_user ON public.consent_audit_log USING btree (user_id, created_at DESC);


--
-- Name: idx_data_access_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_data_access_user ON public.data_access_log USING btree (user_id, created_at DESC);


--
-- Name: idx_deletion_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_deletion_status ON public.data_deletion_log USING btree (status, requested_at DESC);


--
-- Name: idx_dietary_trend; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dietary_trend ON public.dietary_trend_analytics USING btree (dietary_type, year, month_number);


--
-- Name: idx_dispute_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dispute_gtin ON public.verdict_dispute_analytics USING btree (gtin, store);


--
-- Name: idx_dispute_verdict; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dispute_verdict ON public.verdict_dispute_analytics USING btree (verdict_key, resolved);


--
-- Name: idx_error_endpoint; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_endpoint ON public.error_analytics USING btree (endpoint, last_seen_at DESC);


--
-- Name: idx_error_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_error_type ON public.error_analytics USING btree (error_type, resolved);


--
-- Name: idx_feature_usage; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feature_usage ON public.feature_usage_analytics USING btree (feature, year, month_number);


--
-- Name: idx_llm_dietary; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_llm_dietary ON public.llm_interaction_analytics USING btree (detected_dietary, year, month_number);


--
-- Name: idx_llm_intent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_llm_intent ON public.llm_interaction_analytics USING btree (detected_intent, year, month_number);


--
-- Name: idx_llm_lang; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_llm_lang ON public.llm_interaction_analytics USING btree (lang, created_at DESC);


--
-- Name: idx_nutrition_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_nutrition_product ON public.nutrition_facts USING btree (product_id);


--
-- Name: idx_ontology_queue_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ontology_queue_group ON public.ontology_improvement_queue USING btree (ontology_group, status);


--
-- Name: idx_ontology_queue_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ontology_queue_status ON public.ontology_improvement_queue USING btree (status, priority DESC);


--
-- Name: idx_price_analytics_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_price_analytics_category ON public.price_analytics USING btree (category, price_date DESC);


--
-- Name: idx_price_analytics_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_price_analytics_gtin ON public.price_analytics USING btree (gtin, store, price_date DESC);


--
-- Name: idx_price_analytics_store; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_price_analytics_store ON public.price_analytics USING btree (store, price_date DESC);


--
-- Name: idx_price_analytics_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_price_analytics_time ON public.price_analytics USING btree (year, month_number, week_number);


--
-- Name: idx_price_hist_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_price_hist_gtin ON public.price_history USING btree (gtin, store, price_date DESC);


--
-- Name: idx_price_hist_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_price_hist_product ON public.price_history USING btree (product_id, price_date DESC);


--
-- Name: idx_prices_gtin_store; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prices_gtin_store ON public.product_prices USING btree (gtin, store, price_date DESC);


--
-- Name: idx_prices_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prices_product ON public.product_prices USING btree (product_id, price_date DESC);


--
-- Name: idx_prices_store_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prices_store_date ON public.product_prices USING btree (store, price_date DESC);


--
-- Name: idx_product_performance_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_performance_category ON public.product_performance USING btree (category, total_scans DESC);


--
-- Name: idx_product_performance_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_performance_gtin ON public.product_performance USING btree (gtin, store);


--
-- Name: idx_product_performance_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_performance_time ON public.product_performance USING btree (year, month_number);


--
-- Name: idx_products_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_active ON public.products USING btree (is_active, store);


--
-- Name: idx_products_allergens; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_allergens ON public.products USING gin (allergens);


--
-- Name: idx_products_brand; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_brand ON public.products USING btree (brand);


--
-- Name: idx_products_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_category ON public.products USING btree (category, sub_category);


--
-- Name: idx_products_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_gtin ON public.products USING btree (gtin);


--
-- Name: idx_products_gtin_store; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_gtin_store ON public.products USING btree (gtin, store);


--
-- Name: idx_products_image_dead; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_image_dead ON public.products USING btree (image_url_is_dead) WHERE (image_url_is_dead = true);


--
-- Name: idx_products_image_unverified; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_image_unverified ON public.products USING btree (image_url_verified_at) WHERE ((image_url_verified_at IS NULL) AND (image_url IS NOT NULL));


--
-- Name: idx_products_ontology_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_ontology_tags ON public.products USING gin (ontology_tags);


--
-- Name: idx_products_search_de; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_search_de ON public.products USING gin (to_tsvector('german'::regconfig, COALESCE(name_de, ''::text)));


--
-- Name: idx_products_search_en; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_search_en ON public.products USING gin (to_tsvector('english'::regconfig, COALESCE(name_en, ''::text)));


--
-- Name: idx_products_search_fr; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_search_fr ON public.products USING gin (to_tsvector('french'::regconfig, COALESCE(name_fr, ''::text)));


--
-- Name: idx_products_search_it; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_search_it ON public.products USING gin (to_tsvector('italian'::regconfig, COALESCE(name_it, ''::text)));


--
-- Name: idx_regional_dietary; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_regional_dietary ON public.swiss_regional_analytics USING btree (region, dietary_type, year, month_number);


--
-- Name: idx_search_analytics_query; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_search_analytics_query ON public.search_analytics USING btree (query);


--
-- Name: idx_search_analytics_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_search_analytics_time ON public.search_analytics USING btree (year, month_number, created_at DESC);


--
-- Name: idx_session_platform; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_session_platform ON public.session_analytics USING btree (platform, started_at DESC);


--
-- Name: idx_session_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_session_time ON public.session_analytics USING btree (year, month_number, week_number);


--
-- Name: idx_session_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_session_user ON public.session_analytics USING btree (user_id, started_at DESC);


--
-- Name: idx_snapshot_cheapest; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_snapshot_cheapest ON public.store_price_snapshot USING btree (cheapest_store, snapshot_date DESC);


--
-- Name: idx_snapshot_gtin_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_snapshot_gtin_date ON public.store_price_snapshot USING btree (gtin, snapshot_date DESC);


--
-- Name: idx_store_comparison_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_store_comparison_category ON public.store_comparison_analytics USING btree (category, comparison_date DESC);


--
-- Name: idx_store_comparison_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_store_comparison_gtin ON public.store_comparison_analytics USING btree (gtin, comparison_date DESC);


--
-- Name: idx_unified_members_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_unified_members_product ON public.unified_product_members USING btree (product_id);


--
-- Name: idx_unified_one_master; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_unified_one_master ON public.unified_product_members USING btree (unified_id) WHERE (is_master = true);


--
-- Name: idx_user_analytics_event; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_analytics_event ON public.user_analytics USING btree (event_type, created_at DESC);


--
-- Name: idx_user_analytics_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_analytics_session ON public.user_analytics USING btree (session_id, created_at DESC);


--
-- Name: idx_user_analytics_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_analytics_time ON public.user_analytics USING btree (year, month_number, week_number);


--
-- Name: idx_user_analytics_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_analytics_user ON public.user_analytics USING btree (user_id, created_at DESC);


--
-- Name: idx_user_feedback_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_feedback_gtin ON public.user_feedback USING btree (gtin, verdict_key);


--
-- Name: idx_user_feedback_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_feedback_user ON public.user_feedback USING btree (user_id, created_at DESC);


--
-- Name: idx_user_list_items_list; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_list_items_list ON public.user_list_items USING btree (list_id);


--
-- Name: idx_user_lists_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_lists_user ON public.user_lists USING btree (user_id);


--
-- Name: idx_user_prefs_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_prefs_user ON public.user_preferences USING btree (user_id);


--
-- Name: idx_user_saved_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_user_saved_unique ON public.user_saved_products USING btree (user_id, gtin, COALESCE(store, ''::text));


--
-- Name: idx_user_saved_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_saved_user ON public.user_saved_products USING btree (user_id, saved_at DESC);


--
-- Name: idx_user_scans_gtin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_scans_gtin ON public.user_scans USING btree (gtin);


--
-- Name: idx_user_scans_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_scans_user ON public.user_scans USING btree (user_id, scanned_at DESC);


--
-- Name: idx_user_searches_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_searches_user ON public.user_searches USING btree (user_id, searched_at DESC);


--
-- Name: idx_verdict_analytics_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_verdict_analytics_key ON public.verdict_analytics USING btree (verdict_key, year, month_number);


--
-- Name: product_prices trg_append_price_history; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_append_price_history AFTER INSERT OR UPDATE ON public.product_prices FOR EACH ROW EXECUTE FUNCTION public.fn_append_price_history();


--
-- Name: nutrition_facts trg_clear_nutrition_cache; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_clear_nutrition_cache AFTER DELETE ON public.nutrition_facts FOR EACH ROW EXECUTE FUNCTION public.fn_clear_nutrition_cache();


--
-- Name: product_prices trg_compute_unit_prices; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_compute_unit_prices BEFORE INSERT OR UPDATE ON public.product_prices FOR EACH ROW EXECUTE FUNCTION public.fn_compute_unit_prices();


--
-- Name: products trg_products_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: nutrition_facts trg_sync_nutrition_cache; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_sync_nutrition_cache AFTER INSERT OR UPDATE ON public.nutrition_facts FOR EACH ROW EXECUTE FUNCTION public.fn_sync_nutrition_cache();


--
-- Name: unified_product_members trg_sync_unified_master; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_sync_unified_master AFTER INSERT OR UPDATE OF is_master ON public.unified_product_members FOR EACH ROW WHEN ((new.is_master = true)) EXECUTE FUNCTION public.fn_sync_unified_master();


--
-- Name: unified_products trg_unified_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_unified_updated_at BEFORE UPDATE ON public.unified_products FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: user_lists trg_user_lists_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_user_lists_updated_at BEFORE UPDATE ON public.user_lists FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: user_preferences trg_user_prefs_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_user_prefs_updated_at BEFORE UPDATE ON public.user_preferences FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: product_prices trg_validate_price_ref; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_validate_price_ref BEFORE INSERT OR UPDATE ON public.product_prices FOR EACH ROW EXECUTE FUNCTION public.fn_validate_price_product_ref();


--
-- Name: scrape_failures scrape_failures_job_id_fkey; Type: FK CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scrape_failures
    ADD CONSTRAINT scrape_failures_job_id_fkey FOREIGN KEY (job_id) REFERENCES etl.scraper_jobs(id);


--
-- Name: scraper_change_log scraper_change_log_job_id_fkey; Type: FK CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scraper_change_log
    ADD CONSTRAINT scraper_change_log_job_id_fkey FOREIGN KEY (job_id) REFERENCES etl.scraper_jobs(id);


--
-- Name: scraper_jobs scraper_jobs_store_fkey; Type: FK CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.scraper_jobs
    ADD CONSTRAINT scraper_jobs_store_fkey FOREIGN KEY (store) REFERENCES etl.scraper_sources(store);


--
-- Name: staging_products staging_products_job_id_fkey; Type: FK CONSTRAINT; Schema: etl; Owner: postgres
--

ALTER TABLE ONLY etl.staging_products
    ADD CONSTRAINT staging_products_job_id_fkey FOREIGN KEY (job_id) REFERENCES etl.scraper_jobs(id);


--
-- Name: nutrition_facts nutrition_facts_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nutrition_facts
    ADD CONSTRAINT nutrition_facts_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: ontology_current ontology_current_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ontology_current
    ADD CONSTRAINT ontology_current_version_fkey FOREIGN KEY (version) REFERENCES public.ontology_versions(version);


--
-- Name: price_history price_history_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.price_history
    ADD CONSTRAINT price_history_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: product_prices product_prices_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_prices
    ADD CONSTRAINT product_prices_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: products products_ontology_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_ontology_version_fkey FOREIGN KEY (ontology_version) REFERENCES public.ontology_versions(version);


--
-- Name: unified_product_members unified_product_members_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unified_product_members
    ADD CONSTRAINT unified_product_members_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: unified_product_members unified_product_members_unified_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unified_product_members
    ADD CONSTRAINT unified_product_members_unified_id_fkey FOREIGN KEY (unified_id) REFERENCES public.unified_products(unified_id) ON DELETE CASCADE;


--
-- Name: unified_products unified_products_master_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unified_products
    ADD CONSTRAINT unified_products_master_product_id_fkey FOREIGN KEY (master_product_id) REFERENCES public.products(id);


--
-- Name: user_list_items user_list_items_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_list_items
    ADD CONSTRAINT user_list_items_list_id_fkey FOREIGN KEY (list_id) REFERENCES public.user_lists(id) ON DELETE CASCADE;


--
-- Name: agent_execution_log; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.agent_execution_log ENABLE ROW LEVEL SECURITY;

--
-- Name: allergen_alert_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.allergen_alert_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: api_usage_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.api_usage_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: app_behaviour_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.app_behaviour_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: b2b_report_access_log; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.b2b_report_access_log ENABLE ROW LEVEL SECURITY;

--
-- Name: barcode_aliases; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.barcode_aliases ENABLE ROW LEVEL SECURITY;

--
-- Name: category_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.category_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: consent_audit_log; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.consent_audit_log ENABLE ROW LEVEL SECURITY;

--
-- Name: data_access_log; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.data_access_log ENABLE ROW LEVEL SECURITY;

--
-- Name: data_deletion_log; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.data_deletion_log ENABLE ROW LEVEL SECURITY;

--
-- Name: dietary_trend_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.dietary_trend_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: error_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.error_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: feature_usage_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.feature_usage_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: llm_interaction_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.llm_interaction_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: nutrition_facts; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.nutrition_facts ENABLE ROW LEVEL SECURITY;

--
-- Name: ontology_current; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.ontology_current ENABLE ROW LEVEL SECURITY;

--
-- Name: ontology_improvement_queue; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.ontology_improvement_queue ENABLE ROW LEVEL SECURITY;

--
-- Name: ontology_versions; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.ontology_versions ENABLE ROW LEVEL SECURITY;

--
-- Name: price_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.price_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: price_history; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;

--
-- Name: privacy_policy_versions; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.privacy_policy_versions ENABLE ROW LEVEL SECURITY;

--
-- Name: product_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.product_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: product_performance; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.product_performance ENABLE ROW LEVEL SECURITY;

--
-- Name: product_prices; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.product_prices ENABLE ROW LEVEL SECURITY;

--
-- Name: products; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;

--
-- Name: retention_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.retention_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: search_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.search_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: session_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.session_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: store_comparison_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.store_comparison_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: store_price_snapshot; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.store_price_snapshot ENABLE ROW LEVEL SECURITY;

--
-- Name: swiss_regional_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.swiss_regional_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: unified_product_members; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.unified_product_members ENABLE ROW LEVEL SECURITY;

--
-- Name: unified_products; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.unified_products ENABLE ROW LEVEL SECURITY;

--
-- Name: user_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: user_chat_history; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_chat_history ENABLE ROW LEVEL SECURITY;

--
-- Name: user_feedback; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

--
-- Name: user_list_items; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_list_items ENABLE ROW LEVEL SECURITY;

--
-- Name: user_lists; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_lists ENABLE ROW LEVEL SECURITY;

--
-- Name: user_preferences; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

--
-- Name: user_saved_products; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_saved_products ENABLE ROW LEVEL SECURITY;

--
-- Name: user_scans; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_scans ENABLE ROW LEVEL SECURITY;

--
-- Name: user_searches; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.user_searches ENABLE ROW LEVEL SECURITY;

--
-- Name: verdict_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.verdict_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: verdict_dispute_analytics; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.verdict_dispute_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;


--
-- Name: FUNCTION fn_append_price_history(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_append_price_history() TO anon;
GRANT ALL ON FUNCTION public.fn_append_price_history() TO authenticated;
GRANT ALL ON FUNCTION public.fn_append_price_history() TO service_role;


--
-- Name: FUNCTION fn_clear_nutrition_cache(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_clear_nutrition_cache() TO anon;
GRANT ALL ON FUNCTION public.fn_clear_nutrition_cache() TO authenticated;
GRANT ALL ON FUNCTION public.fn_clear_nutrition_cache() TO service_role;


--
-- Name: FUNCTION fn_compute_unit_prices(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_compute_unit_prices() TO anon;
GRANT ALL ON FUNCTION public.fn_compute_unit_prices() TO authenticated;
GRANT ALL ON FUNCTION public.fn_compute_unit_prices() TO service_role;


--
-- Name: FUNCTION fn_iso_week(d date); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_iso_week(d date) TO anon;
GRANT ALL ON FUNCTION public.fn_iso_week(d date) TO authenticated;
GRANT ALL ON FUNCTION public.fn_iso_week(d date) TO service_role;


--
-- Name: FUNCTION fn_rebuild_price_snapshot(p_gtin character varying, p_date date); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_rebuild_price_snapshot(p_gtin character varying, p_date date) TO anon;
GRANT ALL ON FUNCTION public.fn_rebuild_price_snapshot(p_gtin character varying, p_date date) TO authenticated;
GRANT ALL ON FUNCTION public.fn_rebuild_price_snapshot(p_gtin character varying, p_date date) TO service_role;


--
-- Name: FUNCTION fn_rebuild_unified_master(p_unified_id uuid); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_rebuild_unified_master(p_unified_id uuid) TO anon;
GRANT ALL ON FUNCTION public.fn_rebuild_unified_master(p_unified_id uuid) TO authenticated;
GRANT ALL ON FUNCTION public.fn_rebuild_unified_master(p_unified_id uuid) TO service_role;


--
-- Name: FUNCTION fn_set_updated_at(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_set_updated_at() TO anon;
GRANT ALL ON FUNCTION public.fn_set_updated_at() TO authenticated;
GRANT ALL ON FUNCTION public.fn_set_updated_at() TO service_role;


--
-- Name: FUNCTION fn_sync_nutrition_cache(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_sync_nutrition_cache() TO anon;
GRANT ALL ON FUNCTION public.fn_sync_nutrition_cache() TO authenticated;
GRANT ALL ON FUNCTION public.fn_sync_nutrition_cache() TO service_role;


--
-- Name: FUNCTION fn_sync_unified_master(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_sync_unified_master() TO anon;
GRANT ALL ON FUNCTION public.fn_sync_unified_master() TO authenticated;
GRANT ALL ON FUNCTION public.fn_sync_unified_master() TO service_role;


--
-- Name: FUNCTION fn_validate_price_product_ref(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.fn_validate_price_product_ref() TO anon;
GRANT ALL ON FUNCTION public.fn_validate_price_product_ref() TO authenticated;
GRANT ALL ON FUNCTION public.fn_validate_price_product_ref() TO service_role;


--
-- Name: FUNCTION rls_auto_enable(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.rls_auto_enable() TO anon;
GRANT ALL ON FUNCTION public.rls_auto_enable() TO authenticated;
GRANT ALL ON FUNCTION public.rls_auto_enable() TO service_role;


--
-- Name: TABLE agent_execution_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.agent_execution_log TO anon;
GRANT ALL ON TABLE public.agent_execution_log TO authenticated;
GRANT ALL ON TABLE public.agent_execution_log TO service_role;


--
-- Name: TABLE allergen_alert_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.allergen_alert_analytics TO anon;
GRANT ALL ON TABLE public.allergen_alert_analytics TO authenticated;
GRANT ALL ON TABLE public.allergen_alert_analytics TO service_role;


--
-- Name: TABLE allergen_risk_summary; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.allergen_risk_summary TO anon;
GRANT ALL ON TABLE public.allergen_risk_summary TO authenticated;
GRANT ALL ON TABLE public.allergen_risk_summary TO service_role;


--
-- Name: TABLE api_usage_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.api_usage_analytics TO anon;
GRANT ALL ON TABLE public.api_usage_analytics TO authenticated;
GRANT ALL ON TABLE public.api_usage_analytics TO service_role;


--
-- Name: TABLE app_behaviour_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.app_behaviour_analytics TO anon;
GRANT ALL ON TABLE public.app_behaviour_analytics TO authenticated;
GRANT ALL ON TABLE public.app_behaviour_analytics TO service_role;


--
-- Name: TABLE app_mode_usage; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.app_mode_usage TO anon;
GRANT ALL ON TABLE public.app_mode_usage TO authenticated;
GRANT ALL ON TABLE public.app_mode_usage TO service_role;


--
-- Name: TABLE b2b_report_access_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.b2b_report_access_log TO anon;
GRANT ALL ON TABLE public.b2b_report_access_log TO authenticated;
GRANT ALL ON TABLE public.b2b_report_access_log TO service_role;


--
-- Name: TABLE barcode_aliases; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.barcode_aliases TO anon;
GRANT ALL ON TABLE public.barcode_aliases TO authenticated;
GRANT ALL ON TABLE public.barcode_aliases TO service_role;


--
-- Name: TABLE category_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.category_analytics TO anon;
GRANT ALL ON TABLE public.category_analytics TO authenticated;
GRANT ALL ON TABLE public.category_analytics TO service_role;


--
-- Name: TABLE consent_audit_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.consent_audit_log TO anon;
GRANT ALL ON TABLE public.consent_audit_log TO authenticated;
GRANT ALL ON TABLE public.consent_audit_log TO service_role;


--
-- Name: TABLE data_access_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.data_access_log TO anon;
GRANT ALL ON TABLE public.data_access_log TO authenticated;
GRANT ALL ON TABLE public.data_access_log TO service_role;


--
-- Name: TABLE data_deletion_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.data_deletion_log TO anon;
GRANT ALL ON TABLE public.data_deletion_log TO authenticated;
GRANT ALL ON TABLE public.data_deletion_log TO service_role;


--
-- Name: TABLE dietary_trend_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.dietary_trend_analytics TO anon;
GRANT ALL ON TABLE public.dietary_trend_analytics TO authenticated;
GRANT ALL ON TABLE public.dietary_trend_analytics TO service_role;


--
-- Name: TABLE verdict_dispute_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.verdict_dispute_analytics TO anon;
GRANT ALL ON TABLE public.verdict_dispute_analytics TO authenticated;
GRANT ALL ON TABLE public.verdict_dispute_analytics TO service_role;


--
-- Name: TABLE disputed_verdicts_summary; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.disputed_verdicts_summary TO anon;
GRANT ALL ON TABLE public.disputed_verdicts_summary TO authenticated;
GRANT ALL ON TABLE public.disputed_verdicts_summary TO service_role;


--
-- Name: TABLE error_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.error_analytics TO anon;
GRANT ALL ON TABLE public.error_analytics TO authenticated;
GRANT ALL ON TABLE public.error_analytics TO service_role;


--
-- Name: TABLE feature_usage_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.feature_usage_analytics TO anon;
GRANT ALL ON TABLE public.feature_usage_analytics TO authenticated;
GRANT ALL ON TABLE public.feature_usage_analytics TO service_role;


--
-- Name: TABLE feature_popularity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.feature_popularity TO anon;
GRANT ALL ON TABLE public.feature_popularity TO authenticated;
GRANT ALL ON TABLE public.feature_popularity TO service_role;


--
-- Name: TABLE llm_interaction_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.llm_interaction_analytics TO anon;
GRANT ALL ON TABLE public.llm_interaction_analytics TO authenticated;
GRANT ALL ON TABLE public.llm_interaction_analytics TO service_role;


--
-- Name: TABLE llm_quality_summary; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.llm_quality_summary TO anon;
GRANT ALL ON TABLE public.llm_quality_summary TO authenticated;
GRANT ALL ON TABLE public.llm_quality_summary TO service_role;


--
-- Name: TABLE nutrition_facts; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.nutrition_facts TO anon;
GRANT ALL ON TABLE public.nutrition_facts TO authenticated;
GRANT ALL ON TABLE public.nutrition_facts TO service_role;


--
-- Name: TABLE ontology_current; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.ontology_current TO anon;
GRANT ALL ON TABLE public.ontology_current TO authenticated;
GRANT ALL ON TABLE public.ontology_current TO service_role;


--
-- Name: TABLE ontology_improvement_queue; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.ontology_improvement_queue TO anon;
GRANT ALL ON TABLE public.ontology_improvement_queue TO authenticated;
GRANT ALL ON TABLE public.ontology_improvement_queue TO service_role;


--
-- Name: TABLE ontology_priority_queue; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.ontology_priority_queue TO anon;
GRANT ALL ON TABLE public.ontology_priority_queue TO authenticated;
GRANT ALL ON TABLE public.ontology_priority_queue TO service_role;


--
-- Name: TABLE ontology_versions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.ontology_versions TO anon;
GRANT ALL ON TABLE public.ontology_versions TO authenticated;
GRANT ALL ON TABLE public.ontology_versions TO service_role;


--
-- Name: TABLE price_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.price_analytics TO anon;
GRANT ALL ON TABLE public.price_analytics TO authenticated;
GRANT ALL ON TABLE public.price_analytics TO service_role;


--
-- Name: TABLE price_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.price_history TO anon;
GRANT ALL ON TABLE public.price_history TO authenticated;
GRANT ALL ON TABLE public.price_history TO service_role;


--
-- Name: TABLE price_intelligence; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.price_intelligence TO anon;
GRANT ALL ON TABLE public.price_intelligence TO authenticated;
GRANT ALL ON TABLE public.price_intelligence TO service_role;


--
-- Name: TABLE privacy_policy_versions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.privacy_policy_versions TO anon;
GRANT ALL ON TABLE public.privacy_policy_versions TO authenticated;
GRANT ALL ON TABLE public.privacy_policy_versions TO service_role;


--
-- Name: TABLE product_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.product_analytics TO anon;
GRANT ALL ON TABLE public.product_analytics TO authenticated;
GRANT ALL ON TABLE public.product_analytics TO service_role;


--
-- Name: TABLE product_performance; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.product_performance TO anon;
GRANT ALL ON TABLE public.product_performance TO authenticated;
GRANT ALL ON TABLE public.product_performance TO service_role;


--
-- Name: TABLE product_popularity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.product_popularity TO anon;
GRANT ALL ON TABLE public.product_popularity TO authenticated;
GRANT ALL ON TABLE public.product_popularity TO service_role;


--
-- Name: TABLE product_prices; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.product_prices TO anon;
GRANT ALL ON TABLE public.product_prices TO authenticated;
GRANT ALL ON TABLE public.product_prices TO service_role;


--
-- Name: TABLE products; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.products TO anon;
GRANT ALL ON TABLE public.products TO authenticated;
GRANT ALL ON TABLE public.products TO service_role;


--
-- Name: TABLE retention_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.retention_analytics TO anon;
GRANT ALL ON TABLE public.retention_analytics TO authenticated;
GRANT ALL ON TABLE public.retention_analytics TO service_role;


--
-- Name: TABLE search_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.search_analytics TO anon;
GRANT ALL ON TABLE public.search_analytics TO authenticated;
GRANT ALL ON TABLE public.search_analytics TO service_role;


--
-- Name: TABLE session_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.session_analytics TO anon;
GRANT ALL ON TABLE public.session_analytics TO authenticated;
GRANT ALL ON TABLE public.session_analytics TO service_role;


--
-- Name: TABLE session_quality; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.session_quality TO anon;
GRANT ALL ON TABLE public.session_quality TO authenticated;
GRANT ALL ON TABLE public.session_quality TO service_role;


--
-- Name: TABLE store_comparison_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.store_comparison_analytics TO anon;
GRANT ALL ON TABLE public.store_comparison_analytics TO authenticated;
GRANT ALL ON TABLE public.store_comparison_analytics TO service_role;


--
-- Name: TABLE store_price_snapshot; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.store_price_snapshot TO anon;
GRANT ALL ON TABLE public.store_price_snapshot TO authenticated;
GRANT ALL ON TABLE public.store_price_snapshot TO service_role;


--
-- Name: TABLE swiss_regional_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.swiss_regional_analytics TO anon;
GRANT ALL ON TABLE public.swiss_regional_analytics TO authenticated;
GRANT ALL ON TABLE public.swiss_regional_analytics TO service_role;


--
-- Name: TABLE swiss_dietary_demand; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.swiss_dietary_demand TO anon;
GRANT ALL ON TABLE public.swiss_dietary_demand TO authenticated;
GRANT ALL ON TABLE public.swiss_dietary_demand TO service_role;


--
-- Name: TABLE unified_product_members; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.unified_product_members TO anon;
GRANT ALL ON TABLE public.unified_product_members TO authenticated;
GRANT ALL ON TABLE public.unified_product_members TO service_role;


--
-- Name: TABLE unified_products; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.unified_products TO anon;
GRANT ALL ON TABLE public.unified_products TO authenticated;
GRANT ALL ON TABLE public.unified_products TO service_role;


--
-- Name: TABLE user_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_analytics TO anon;
GRANT ALL ON TABLE public.user_analytics TO authenticated;
GRANT ALL ON TABLE public.user_analytics TO service_role;


--
-- Name: TABLE user_chat_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_chat_history TO anon;
GRANT ALL ON TABLE public.user_chat_history TO authenticated;
GRANT ALL ON TABLE public.user_chat_history TO service_role;


--
-- Name: TABLE user_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_feedback TO anon;
GRANT ALL ON TABLE public.user_feedback TO authenticated;
GRANT ALL ON TABLE public.user_feedback TO service_role;


--
-- Name: TABLE user_growth; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_growth TO anon;
GRANT ALL ON TABLE public.user_growth TO authenticated;
GRANT ALL ON TABLE public.user_growth TO service_role;


--
-- Name: TABLE user_list_items; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_list_items TO anon;
GRANT ALL ON TABLE public.user_list_items TO authenticated;
GRANT ALL ON TABLE public.user_list_items TO service_role;


--
-- Name: TABLE user_lists; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_lists TO anon;
GRANT ALL ON TABLE public.user_lists TO authenticated;
GRANT ALL ON TABLE public.user_lists TO service_role;


--
-- Name: TABLE user_preferences; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_preferences TO anon;
GRANT ALL ON TABLE public.user_preferences TO authenticated;
GRANT ALL ON TABLE public.user_preferences TO service_role;


--
-- Name: TABLE user_saved_products; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_saved_products TO anon;
GRANT ALL ON TABLE public.user_saved_products TO authenticated;
GRANT ALL ON TABLE public.user_saved_products TO service_role;


--
-- Name: TABLE user_scans; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_scans TO anon;
GRANT ALL ON TABLE public.user_scans TO authenticated;
GRANT ALL ON TABLE public.user_scans TO service_role;


--
-- Name: TABLE user_searches; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_searches TO anon;
GRANT ALL ON TABLE public.user_searches TO authenticated;
GRANT ALL ON TABLE public.user_searches TO service_role;


--
-- Name: TABLE v_active_promotions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_active_promotions TO anon;
GRANT ALL ON TABLE public.v_active_promotions TO authenticated;
GRANT ALL ON TABLE public.v_active_promotions TO service_role;


--
-- Name: TABLE v_allergen_risk; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_allergen_risk TO anon;
GRANT ALL ON TABLE public.v_allergen_risk TO authenticated;
GRANT ALL ON TABLE public.v_allergen_risk TO service_role;


--
-- Name: TABLE v_api_performance; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_api_performance TO anon;
GRANT ALL ON TABLE public.v_api_performance TO authenticated;
GRANT ALL ON TABLE public.v_api_performance TO service_role;


--
-- Name: TABLE v_app_mode_usage; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_app_mode_usage TO anon;
GRANT ALL ON TABLE public.v_app_mode_usage TO authenticated;
GRANT ALL ON TABLE public.v_app_mode_usage TO service_role;


--
-- Name: TABLE v_basket_prices; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_basket_prices TO anon;
GRANT ALL ON TABLE public.v_basket_prices TO authenticated;
GRANT ALL ON TABLE public.v_basket_prices TO service_role;


--
-- Name: TABLE v_best_value; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_best_value TO anon;
GRANT ALL ON TABLE public.v_best_value TO authenticated;
GRANT ALL ON TABLE public.v_best_value TO service_role;


--
-- Name: TABLE v_disputed_verdicts; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_disputed_verdicts TO anon;
GRANT ALL ON TABLE public.v_disputed_verdicts TO authenticated;
GRANT ALL ON TABLE public.v_disputed_verdicts TO service_role;


--
-- Name: TABLE v_error_health; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_error_health TO anon;
GRANT ALL ON TABLE public.v_error_health TO authenticated;
GRANT ALL ON TABLE public.v_error_health TO service_role;


--
-- Name: TABLE v_feature_popularity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_feature_popularity TO anon;
GRANT ALL ON TABLE public.v_feature_popularity TO authenticated;
GRANT ALL ON TABLE public.v_feature_popularity TO service_role;


--
-- Name: TABLE v_llm_quality; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_llm_quality TO anon;
GRANT ALL ON TABLE public.v_llm_quality TO authenticated;
GRANT ALL ON TABLE public.v_llm_quality TO service_role;


--
-- Name: TABLE v_ontology_priority; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_ontology_priority TO anon;
GRANT ALL ON TABLE public.v_ontology_priority TO authenticated;
GRANT ALL ON TABLE public.v_ontology_priority TO service_role;


--
-- Name: TABLE v_price_comparison; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_price_comparison TO anon;
GRANT ALL ON TABLE public.v_price_comparison TO authenticated;
GRANT ALL ON TABLE public.v_price_comparison TO service_role;


--
-- Name: TABLE v_price_history_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_price_history_stats TO anon;
GRANT ALL ON TABLE public.v_price_history_stats TO authenticated;
GRANT ALL ON TABLE public.v_price_history_stats TO service_role;


--
-- Name: TABLE v_price_intelligence; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_price_intelligence TO anon;
GRANT ALL ON TABLE public.v_price_intelligence TO authenticated;
GRANT ALL ON TABLE public.v_price_intelligence TO service_role;


--
-- Name: TABLE v_product_popularity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_product_popularity TO anon;
GRANT ALL ON TABLE public.v_product_popularity TO authenticated;
GRANT ALL ON TABLE public.v_product_popularity TO service_role;


--
-- Name: TABLE v_scraper_health; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_scraper_health TO anon;
GRANT ALL ON TABLE public.v_scraper_health TO authenticated;
GRANT ALL ON TABLE public.v_scraper_health TO service_role;


--
-- Name: TABLE v_session_quality; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_session_quality TO anon;
GRANT ALL ON TABLE public.v_session_quality TO authenticated;
GRANT ALL ON TABLE public.v_session_quality TO service_role;


--
-- Name: TABLE v_swiss_dietary_demand; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_swiss_dietary_demand TO anon;
GRANT ALL ON TABLE public.v_swiss_dietary_demand TO authenticated;
GRANT ALL ON TABLE public.v_swiss_dietary_demand TO service_role;


--
-- Name: TABLE v_user_growth; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_user_growth TO anon;
GRANT ALL ON TABLE public.v_user_growth TO authenticated;
GRANT ALL ON TABLE public.v_user_growth TO service_role;


--
-- Name: TABLE verdict_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.verdict_analytics TO anon;
GRANT ALL ON TABLE public.verdict_analytics TO authenticated;
GRANT ALL ON TABLE public.verdict_analytics TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- PostgreSQL database dump complete
--

\unrestrict nzeaIJM9lJaLCc7PZ55wX3AxaNPzikwmchUSNFB6uXH2m9beo5UtcKD2zgFzWJo

