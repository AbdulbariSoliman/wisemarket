-- ============================================================
-- 003 — Seed ontology versions
-- products.ontology_version references ontology_versions(version).
-- The ETL scripts write 'v1.0' (supabase_ingest.py) and 'v2.0'
-- (scraper_migros.py, ingest_open_food_facts.py), so both must exist
-- before ingestion can run on a fresh database. Idempotent.
-- ============================================================
INSERT INTO public.ontology_versions (version, notes) VALUES
    ('v1.0', 'Initial ontology (66 categories, EN/DE/FR/IT)'),
    ('v2.0', 'Expanded category routing; used by the Migros scraper and Open Food Facts ingestion')
ON CONFLICT (version) DO NOTHING;

INSERT INTO public.ontology_current (lock, version)
VALUES (true, 'v2.0')
ON CONFLICT (lock) DO NOTHING;
