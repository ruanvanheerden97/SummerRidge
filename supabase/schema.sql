-- =============================================================
-- Summer Ridge Smart Metering — Supabase schema
-- Run this once in the Supabase SQL Editor (Dashboard > SQL Editor)
-- =============================================================

-- Meter register, synced automatically from data/Summer_Ridge_Master_Sheet.xlsx
-- on every import run. The Excel file in the GitHub repo stays the source of truth.
create table if not exists meters (
    serial        text primary key,
    stand         text not null,
    utility       text not null check (utility in ('elec', 'gas')),
    floor         text not null,           -- '01'..'08' or 'Communal / Bulk'
    parent_meter  text,
    model         text,
    amr_active    boolean not null default false,
    updated_at    timestamptz not null default now()
);

create index if not exists idx_meters_stand   on meters (stand);
create index if not exists idx_meters_utility on meters (utility);

-- Every AMR reading ever imported (full history).
-- reading_value is stored exactly as received from the SFTP CSV:
--   gas  = litres  (divide by 1000 for m3 — done in the app)
--   elec = kWh
create table if not exists readings (
    id            bigint generated always as identity primary key,
    meter_serial  text not null,
    reading_ts    timestamptz not null,    -- READING_DATE from the CSV
    reading_value numeric not null,        -- READING_VALUE (raw, cumulative index)
    peak          numeric,                 -- PEAK     (elec TOU registers, when present)
    std           numeric,                 -- STD
    offpeak       numeric,                 -- OFFPEAK
    md            numeric,                 -- MD (maximum demand)
    low_battery   boolean not null default false,
    exported_at   timestamptz,             -- CURRENT_DATE column from the CSV
    source_file   text,
    imported_at   timestamptz not null default now(),
    unique (meter_serial, reading_ts)      -- makes re-imports idempotent
);

create index if not exists idx_readings_serial_ts on readings (meter_serial, reading_ts desc);
create index if not exists idx_readings_ts        on readings (reading_ts desc);

-- One row per CSV file processed from the SFTP server, so files are never
-- imported twice and you can audit what came in and when.
create table if not exists import_log (
    file_name     text primary key,
    processed_at  timestamptz not null default now(),
    rows_in_file  integer not null default 0,
    rows_inserted integer not null default 0,
    rows_skipped  integer not null default 0,
    status        text not null default 'ok',   -- 'ok' | 'error'
    error_detail  text
);

-- Convenience view: latest reading per meter, joined to the register.
create or replace view latest_readings as
select distinct on (r.meter_serial)
    r.meter_serial,
    r.reading_ts,
    r.reading_value,
    r.peak, r.std, r.offpeak, r.md,
    r.low_battery,
    r.imported_at,
    m.stand,
    m.utility,
    m.floor,
    m.amr_active
from readings r
left join meters m on m.serial = r.meter_serial
order by r.meter_serial, r.reading_ts desc;

-- -------------------------------------------------------------
-- Row Level Security
-- The Streamlit app reads with the anon key (read-only);
-- the GitHub Action writes with the service_role key (bypasses RLS).
-- -------------------------------------------------------------
alter table meters     enable row level security;
alter table readings   enable row level security;
alter table import_log enable row level security;

create policy "public read meters"     on meters     for select using (true);
create policy "public read readings"   on readings   for select using (true);
create policy "public read import_log" on import_log for select using (true);
