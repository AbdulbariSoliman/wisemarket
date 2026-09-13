-- backend/schema/migrations/002_unified_merge_fields.sql
-- Adds ingredients + nutrition to the canonical record, and a
-- field->source provenance map. Idempotent (IF NOT EXISTS).

ALTER TABLE public.unified_products
    ADD COLUMN IF NOT EXISTS canonical_ingredients_raw text,
    ADD COLUMN IF NOT EXISTS canonical_nutrition jsonb,
    ADD COLUMN IF NOT EXISTS field_sources jsonb DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.unified_products.field_sources IS
'Maps each canonical field to its provenance, e.g.
 {"name":{"store":"migros","kind":"retailer"},
  "price_ref":{"store":"migros","kind":"retailer"},
  "image":{"store":"migros","kind":"retailer"},
  "category":{"store":"migros","kind":"retailer"},
  "source_url":{"store":"migros","kind":"retailer"},
  "allergens":{"store":"open_food_facts","kind":"third_party"},
  "ingredients":{"store":"open_food_facts","kind":"third_party"},
  "nutrition":{"store":"open_food_facts","kind":"third_party"}}.
 kind in (retailer, third_party). ontology_tags is decision-engine-computed, not sourced.';