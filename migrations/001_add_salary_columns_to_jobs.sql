ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS salary_min_eur integer,
    ADD COLUMN IF NOT EXISTS salary_max_eur integer;
