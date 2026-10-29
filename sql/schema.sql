-- Schema for the production analytics database (SQLite)

DROP TABLE IF EXISTS machines;
DROP TABLE IF EXISTS shift_output;
DROP TABLE IF EXISTS downtime_events;

CREATE TABLE machines (
    machine_id     TEXT PRIMARY KEY,
    process_step   TEXT NOT NULL,
    ideal_cycle_s  REAL NOT NULL   -- ideal seconds per unit
);

CREATE TABLE shift_output (
    machine_id    TEXT NOT NULL REFERENCES machines(machine_id),
    prod_date     TEXT NOT NULL,   -- ISO date
    shift         TEXT NOT NULL,   -- Frueh / Spaet / Nacht
    planned_min   INTEGER NOT NULL,
    downtime_min  INTEGER NOT NULL,
    units_total   INTEGER NOT NULL,
    units_scrap   INTEGER NOT NULL,
    PRIMARY KEY (machine_id, prod_date, shift)
);

CREATE TABLE downtime_events (
    event_id    INTEGER PRIMARY KEY,
    machine_id  TEXT NOT NULL REFERENCES machines(machine_id),
    prod_date   TEXT NOT NULL,
    shift       TEXT NOT NULL,
    reason      TEXT NOT NULL,
    minutes     INTEGER NOT NULL
);

CREATE INDEX idx_out_date ON shift_output(prod_date);
CREATE INDEX idx_dt_machine ON downtime_events(machine_id);
