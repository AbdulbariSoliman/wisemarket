-- ============================================================
-- WISEMARKET — TEST SEED DATA (integration tests only)
-- Idempotent: safe to re-run. Matches GTINs asserted in tests/test_api.py.
-- Apply AFTER backend/schema/schema.sql against the local Supabase Postgres.
--   psql "$DB_URL" -f backend/schema/seed_test.sql
-- ============================================================

DELETE FROM public.product_prices       WHERE gtin IN ('7610000100001','7610000200001','7610000500001','7610001100001');
DELETE FROM public.store_price_snapshot  WHERE gtin IN ('7610000100001','7610000500001','7610001100001');
DELETE FROM public.products              WHERE gtin IN ('7610000100001','7610000200001','7610000500001','7610001100001');

INSERT INTO public.products (gtin, store, name_en, name_de, category, brand, ingredients_raw, ontology_tags, allergens, is_active, is_verified)
VALUES
 ('7610000100001','migros','Whole Milk 1L','Vollmilch 1L','dairy','M-Classic','Milk, Vitamin D3',
    '{"halal": true, "vegan": false, "vegetarian": true, "lactose_free": false}'::jsonb,
    '{"contains": ["milk"], "may_contain": []}'::jsonb, true, true),
 ('7610000100001','coop','Whole Milk 1L','Vollmilch 1L','dairy','Qualite & Prix','Milk, Vitamin D3',
    '{"halal": true, "vegan": false, "vegetarian": true}'::jsonb,
    '{"contains": ["milk"], "may_contain": []}'::jsonb, true, true),
 ('7610000100001','aldi','Whole Milk 1L','Vollmilch 1L','dairy','Milfina','Milk, Vitamin D3',
    '{"halal": true, "vegan": false, "vegetarian": true}'::jsonb,
    '{"contains": ["milk"], "may_contain": []}'::jsonb, true, true),
 ('7610000200001','migros','Oat Drink 1L','Haferdrink 1L','dairy_alternative','Oatly','Oat drink (oats, water), calcium, vitamins',
    '{"halal": true, "vegan": true, "vegetarian": true, "lactose_free": true}'::jsonb,
    '{"contains": [], "may_contain": ["nuts"]}'::jsonb, true, true),
 ('7610000500001','migros','Halal Chicken Breast','Halal Poulet','meat','TerraSuisse','Chicken breast',
    '{"halal": true, "vegan": false, "vegetarian": false}'::jsonb,
    '{"contains": [], "may_contain": []}'::jsonb, true, true),
 ('7610001100001','migros','Spaghetti 500g','Spaghetti 500g','pantry','Barilla','Durum wheat semolina',
    '{"halal": true, "vegan": true, "vegetarian": true}'::jsonb,
    '{"contains": ["gluten"], "may_contain": []}'::jsonb, true, true),
 ('7610001100001','coop','Spaghetti 500g','Spaghetti 500g','pantry','Barilla','Durum wheat semolina',
    '{"halal": true, "vegan": true, "vegetarian": true}'::jsonb,
    '{"contains": ["gluten"], "may_contain": []}'::jsonb, true, true);

INSERT INTO public.product_prices (product_id, gtin, store, price_chf, unit_quantity, unit_type, price_date)
SELECT p.id, p.gtin, p.store, v.price, v.qty, v.utype, CURRENT_DATE
FROM (VALUES
    ('7610000100001','migros', 1.45, 1000, 'ml'),
    ('7610000100001','coop',   1.50, 1000, 'ml'),
    ('7610000100001','aldi',   1.29, 1000, 'ml'),
    ('7610000200001','migros', 2.20, 1000, 'ml'),
    ('7610000500001','migros', 8.90,  500, 'g'),
    ('7610001100001','migros', 1.95,  500, 'g'),
    ('7610001100001','coop',   2.10,  500, 'g')
) AS v(gtin, store, price, qty, utype)
JOIN public.products p ON p.gtin = v.gtin AND p.store = v.store;

INSERT INTO public.nutrition_facts (product_id, energy_kcal_100, fat_100, carbs_100, sugars_100, protein_100, salt_100, serving_size_g, energy_kcal_srv, nutri_score, nova_group, source)
SELECT p.id, 64, 3.5, 4.8, 4.8, 3.3, 0.1, 250, 160, 'B', 1, 'seed'
FROM public.products p WHERE p.gtin = '7610000100001' AND p.store IN ('migros', 'coop', 'aldi');

INSERT INTO public.store_price_snapshot
    (gtin, snapshot_date, prices_chf, prices_per_100g, cheapest_store, cheapest_price,
     most_expensive_store, most_expensive_price, price_spread_chf, price_spread_pct, stores_compared)
VALUES
 ('7610000100001', CURRENT_DATE,
    '{"migros": 1.45, "coop": 1.50, "aldi": 1.29}'::jsonb,
    '{"migros": 0.1450, "coop": 0.1500, "aldi": 0.1290}'::jsonb,
    'aldi', 1.29, 'coop', 1.50, 0.21, 16.28, 3);
