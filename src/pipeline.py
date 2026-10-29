"""
Pipeline: CSV -> SQLite -> SQL analysis -> Tableau CSVs + management report.

Run from the project root:
    python src/generate_data.py
    python src/pipeline.py
"""
import sqlite3
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA, SQL = ROOT / "data", ROOT / "sql"
TABLEAU, REPORT = ROOT / "tableau", ROOT / "report"
DB = DATA / "production.db"


def load_db():
    con = sqlite3.connect(DB)
    con.executescript((SQL / "schema.sql").read_text(encoding="utf-8"))
    for table in ["machines", "shift_output", "downtime_events"]:
        df = pd.read_csv(DATA / f"{table}.csv")
        df.to_sql(table, con, if_exists="append", index=False)
    return con


def check_quality(con):
    """Basic data quality checks before analysis."""
    checks = {
        "downtime > planned time":
            "SELECT COUNT(*) FROM shift_output WHERE downtime_min > planned_min",
        "scrap > total units":
            "SELECT COUNT(*) FROM shift_output WHERE units_scrap > units_total",
        "unknown machine in downtime":
            "SELECT COUNT(*) FROM downtime_events d LEFT JOIN machines m "
            "USING (machine_id) WHERE m.machine_id IS NULL",
        "downtime events vs. shift totals mismatch":
            "SELECT COUNT(*) FROM shift_output s LEFT JOIN ("
            " SELECT machine_id, prod_date, shift, SUM(minutes) AS m"
            " FROM downtime_events GROUP BY 1,2,3) d"
            " USING (machine_id, prod_date, shift)"
            " WHERE COALESCE(d.m,0) <> s.downtime_min",
    }
    for name, q in checks.items():
        n = con.execute(q).fetchone()[0]
        status = "OK" if n == 0 else f"FAIL ({n} rows)"
        print(f"  [check] {name}: {status}")


def run_queries(con):
    text = (SQL / "analysis.sql").read_text(encoding="utf-8")
    results = {}
    for block in text.split("-- name: ")[1:]:
        name, _, query = block.partition("\n")
        df = pd.read_sql_query(query, con)
        df.to_csv(TABLEAU / f"{name.strip()}.csv", index=False)
        results[name.strip()] = df
    return results


def charts(r):
    cap = r["capacity_by_step"].sort_values("process_step")
    fig, ax = plt.subplots(figsize=(7, 3.5))
    colors = ["#c0392b" if v == cap.good_units_per_day.min() else "#7f8c8d"
              for v in cap.good_units_per_day]
    ax.bar(cap.process_step.str[3:], cap.good_units_per_day, color=colors)
    ax.set_ylabel("Gutteile pro Tag")
    ax.set_title("Kapazitaet je Prozessschritt (Engpass rot)")
    plt.xticks(rotation=15)
    plt.tight_layout()
    fig.savefig(REPORT / "capacity_by_step.png", dpi=140)
    plt.close(fig)

    p = r["downtime_pareto"]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(p.reason, p.minutes, color="#7f8c8d")
    ax2 = ax.twinx()
    ax2.plot(p.reason, p.cumulative_pct, color="#c0392b", marker="o")
    ax2.set_ylim(0, 105)
    ax.set_ylabel("Minuten")
    ax2.set_ylabel("kumuliert %")
    ax.set_title("Stillstandsgruende (Pareto)")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(REPORT / "downtime_pareto.png", dpi=140)
    plt.close(fig)


def report(r):
    cap = r["capacity_by_step"]
    oee = r["oee_by_machine"]
    par = r["downtime_pareto"]
    scrap = r["scrap_by_shift"]
    trend = r["weekly_trend"]

    bott = cap.iloc[0]
    second = cap.iloc[1]
    gap = second.good_units_per_day - bott.good_units_per_day
    top2 = par.head(2)
    wb = trend[trend.process_step == bott.process_step]
    a_first, a_last = wb.availability.iloc[0], wb.availability.iloc[-1]
    s_bott = scrap[scrap.process_step == bott.process_step]
    worst_shift = s_bott.sort_values("scrap_pct").iloc[-1]

    md = f"""# Management Summary – Engpassanalyse Back-End-Linie

*Synthetische Daten, 12 Wochen, 5 Prozessschritte, 12 Anlagen.*

## Kernaussagen

1. **Engpass: {bott.process_step[3:].replace('_', ' ')}** mit
   {int(bott.good_units_per_day):,} Gutteilen/Tag. Der naechste Schritt
   ({second.process_step[3:].replace('_', ' ')}) schafft
   {int(second.good_units_per_day):,}/Tag – Luecke von
   {int(gap):,} Teilen/Tag.
2. **Verfuegbarkeit am Engpass sinkt** von {a_first:.1%} (Woche 1) auf
   {a_last:.1%} (letzte Woche) – Hinweis auf Verschleiss oder fehlende
   vorbeugende Wartung.
3. **Top-2 Stillstandsgruende** ({top2.reason.iloc[0]},
   {top2.reason.iloc[1]}) verursachen
   {top2.cumulative_pct.iloc[1]:.0f}% der Stillstandszeit.
4. **Ausschuss am Engpass** am hoechsten in Schicht
   {worst_shift['shift']} ({worst_shift.scrap_pct:.2f}%).
5. **Niedrigste OEE:** {oee.iloc[0].machine_id}
   ({oee.iloc[0].oee:.1%}).

## Empfehlungen

- Ruestzeiten am Engpass reduzieren (SMED), da Ruesten der groesste
  Stillstandsgrund ist.
- Vorbeugende Wartung fuer Wire Bonding einplanen und Verfuegbarkeit
  woechentlich tracken.
- Ursachenanalyse Ausschuss Nachtschicht (z. B. Einweisung, Parameter).
- Kurzfristig: Puffer vor dem Engpass sicherstellen, damit er nie auf
  Material wartet.

![Kapazitaet](capacity_by_step.png)
![Pareto](downtime_pareto.png)

## Kennzahlen je Anlage (OEE)

{oee.to_markdown(index=False)}
"""
    (REPORT / "management_summary.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    if DB.exists():
        DB.unlink()
    TABLEAU.mkdir(exist_ok=True)
    REPORT.mkdir(exist_ok=True)
    con = load_db()
    print("Data quality checks:")
    check_quality(con)
    res = run_queries(con)
    charts(res)
    report(res)
    con.close()
    print(f"Exported {len(res)} Tableau datasets to {TABLEAU.name}/")
    print("Report written to report/management_summary.md")
