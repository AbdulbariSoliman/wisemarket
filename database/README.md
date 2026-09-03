# WiseMarket Database

This folder holds the canonical schema for the WiseMarket Supabase project so the
database can be recreated from source control.

- **`schema.sql`** — schema-only dump of the `public` schema (tables, views,
  functions, triggers, indexes, foreign keys, RLS enablement, and role grants).
  Generated with `pg_dump` from the live Supabase project
  (`khwuiovgrblrixsindvj`).

## What's included

| Object type | Count |
|---|---|
| Tables | 44 |
| Views | 17 |
| Functions (plpgsql/sql) | 11 |
| Triggers | 10 |
| Indexes | 90 |
| Foreign keys | 10 |

RLS is **enabled** on every table (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).
Standard Supabase role grants (`anon`, `authenticated`, `service_role`) are
included.

## Recreate the database locally

You need Postgres 15+ (Supabase runs 17). Using the Supabase CLI:

```bash
# start a local stack
supabase start

# apply the schema
psql "$(supabase status -o json | jq -r '.DB.URL')" -f database/schema.sql
```

Or against any Postgres instance:

```bash
createdb wisemarket
psql -d wisemarket -f database/schema.sql
```

## Recreate against a fresh Supabase project

```bash
psql "postgresql://postgres.<project-ref>:<db-password>@aws-0-<region>.pooler.supabase.com:5432/postgres" \
  -f database/schema.sql
```

## Regenerate this dump from the live database

```bash
pg_dump \
  -h aws-1-eu-central-2.pooler.supabase.com -p 5432 \
  -U postgres.khwuiovgrblrixsindvj -d postgres \
  --schema-only --schema=public \
  -f database/schema.sql
```

(The `-U`/host values come from **Supabase Dashboard → Project Settings →
Database → Connection string**. Never commit the password.)

## Known limitations

1. **Only the `public` schema is captured.** The live database also defines
   `analytics.*`, `events.*`, and `etl.*` schemas. Several reporting views
   (`v_allergen_risk`, `v_api_performance`, `v_app_mode_usage`,
   `v_disputed_verdicts`, `v_error_health`, `v_feature_popularity`,
   `v_llm_quality`, `v_price_intelligence`, `v_product_popularity`,
   `v_scraper_health`, `v_session_quality`, `v_swiss_dietary_demand`,
   `v_user_growth`) read from tables in those schemas and were **omitted from
   `schema.sql`** so that the `public` schema restores cleanly on its own.
   `v_ontology_priority` is kept but carries an inline warning because it
   references `etl.ontology_improvement_queue`.

   To make the dump fully self-contained, re-run `pg_dump` with
   `--schema=public --schema=analytics --schema=events --schema=etl` and replace
   this file. See [issue tracker] to complete this.

2. **RLS policies are not included** — only RLS *enablement*. Supabase manages the
   individual `CREATE POLICY` statements; export them separately if needed
   (`pg_dump` includes them when dumping as the table owner).

3. **No seed/reference data.** This is a structural dump only. Export data with
   `pg_dump --data-only` into a separate `seed.sql` if you need it.

## Environment variables

The backend reads Supabase credentials from the environment. See the repo-root
`.env.example` for the full list (`SUPABASE_URL`, `SUPABASE_KEY`, etc.).
