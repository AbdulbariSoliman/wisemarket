# from C:\Users\Abdulbari — move the dump into your repo clone, then:
cd path\to\your\wisemarket
copy C:\Users\Abdulbari\schema.sql .\schema.sql
git checkout -b add-database-schema
git add schema.sql
git commit -m "Add Supabase schema dump (pg_dump, public schema)"
git push -u origin add-database-schema
