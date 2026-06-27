CREATE EXTENSION IF NOT EXISTS unaccent;

-- Arabic text search configuration
CREATE TEXT SEARCH CONFIGURATION arabic (COPY = pg_catalog.simple);
ALTER TEXT SEARCH CONFIGURATION arabic ALTER MAPPING FOR word WITH unaccent, simple;
ALTER TEXT SEARCH CONFIGURATION arabic ALTER MAPPING FOR hword WITH unaccent, simple;
ALTER TEXT SEARCH CONFIGURATION arabic ALTER MAPPING FOR asciiword WITH english_stem;
