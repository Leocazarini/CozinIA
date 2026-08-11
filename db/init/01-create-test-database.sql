-- Runs once, on first initialization of the postgres data volume.
-- POSTGRES_DB already creates the dev database; the test suite needs its
-- own database so it never touches dev data.
CREATE DATABASE cozinia_test;
