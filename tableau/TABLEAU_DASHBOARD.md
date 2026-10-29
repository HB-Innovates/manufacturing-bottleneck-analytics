# Tableau dashboard

The pipeline exports six CSVs in this folder. They are built to be
connected directly in Tableau Public (free) or Tableau Desktop.

| File | Use in dashboard |
|---|---|
| `capacity_by_step.csv` | Bar chart: good units per day by process step (bottleneck) |
| `oee_by_machine.csv` | Highlight table: availability, performance, quality, OEE |
| `downtime_pareto.csv` | Pareto: bars = minutes, line = cumulative % (dual axis) |
| `downtime_by_step_reason.csv` | Stacked bar: downtime reasons per step |
| `scrap_by_shift.csv` | Heatmap: step x shift, colour = scrap % |
| `weekly_trend.csv` | Line chart: availability per week, filter by step |

## Build steps

1. Tableau Public → Connect → Text file → `capacity_by_step.csv`.
2. Add the other CSVs as separate data sources.
3. Build one sheet per row of the table above.
4. Dashboard layout: KPI row (OEE of bottleneck, scrap %, downtime) on
   top, capacity + Pareto in the middle, trend and heatmap below.
5. Add a `process_step` filter and apply it to all related sheets.
6. Published: https://public.tableau.com/views/manufacturing-bottleneck-analytics/Sheet1
