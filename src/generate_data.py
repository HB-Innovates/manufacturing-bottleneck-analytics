"""
Generate a synthetic production dataset for a semiconductor back-end line.

The line has five process steps. Each step has 2-3 machines. For every
machine and shift over 12 weeks we simulate planned time, downtime events,
produced units and scrap. One step (wire bonding) is deliberately
under-sized so the analysis has a real bottleneck to find.

All data is synthetic. No real company data is used.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

START = date(2026, 6, 1)
WEEKS = 12
SHIFTS = ["Frueh", "Spaet", "Nacht"]
SHIFT_MINUTES = 480

# step, machine ids, ideal cycle time (seconds per unit), base availability
STEPS = [
    ("10_Wafer_Test",   ["WT-01", "WT-02"],          9.0, 0.92),
    ("20_Die_Attach",   ["DA-01", "DA-02", "DA-03"], 12.0, 0.90),
    ("30_Wire_Bonding", ["WB-01", "WB-02"],          16.5, 0.84),
    ("40_Molding",      ["MO-01", "MO-02"],          11.0, 0.89),
    ("50_Final_Test",   ["FT-01", "FT-02", "FT-03"], 13.0, 0.91),
]

DOWNTIME_REASONS = [
    ("Ruesten", 0.30),
    ("Materialmangel", 0.18),
    ("Stoerung_Mechanik", 0.20),
    ("Stoerung_Software", 0.10),
    ("Wartung_ungeplant", 0.12),
    ("Warten_auf_Bediener", 0.10),
]


def pick_reason():
    r = random.random()
    acc = 0.0
    for name, p in DOWNTIME_REASONS:
        acc += p
        if r <= acc:
            return name
    return DOWNTIME_REASONS[-1][0]


machines, shifts_rows, downtime_rows = [], [], []
event_id = 1

for step, ids, cycle, base_avail in STEPS:
    for m in ids:
        machines.append(dict(machine_id=m, process_step=step,
                             ideal_cycle_s=cycle))

for d in range(WEEKS * 7):
    day = START + timedelta(days=d)
    if day.weekday() == 6:  # no production on Sundays
        continue
    for step, ids, cycle, base_avail in STEPS:
        for m in ids:
            for shift in SHIFTS:
                # night shift slightly worse, wire bonding degrades over time
                avail = base_avail - (0.03 if shift == "Nacht" else 0.0)
                if step == "30_Wire_Bonding":
                    avail -= 0.002 * (d // 7)
                avail = max(0.6, min(0.98, random.gauss(avail, 0.03)))

                down_total = round(SHIFT_MINUTES * (1 - avail))
                remaining = down_total
                while remaining > 0:
                    dur = min(remaining, random.randint(5, 45))
                    downtime_rows.append(dict(
                        event_id=event_id, machine_id=m,
                        prod_date=day.isoformat(), shift=shift,
                        reason=pick_reason(), minutes=dur))
                    event_id += 1
                    remaining -= dur

                run_min = SHIFT_MINUTES - down_total
                perf = max(0.7, min(0.99, random.gauss(0.90, 0.04)))
                units = int(run_min * 60 / cycle * perf)
                scrap_rate = random.gauss(0.018, 0.006)
                if step == "30_Wire_Bonding":
                    scrap_rate += 0.012
                if shift == "Nacht":
                    scrap_rate += 0.004
                scrap = max(0, int(units * max(0.0, scrap_rate)))

                shifts_rows.append(dict(
                    machine_id=m, prod_date=day.isoformat(), shift=shift,
                    planned_min=SHIFT_MINUTES, downtime_min=down_total,
                    units_total=units, units_scrap=scrap))


def write(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


write("machines.csv", machines)
write("shift_output.csv", shifts_rows)
write("downtime_events.csv", downtime_rows)
