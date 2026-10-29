-- Each query starts with a "name" marker line (see below).
-- src/pipeline.py runs them and exports every result as CSV for Tableau.

-- name: oee_by_machine
-- OEE = Availability x Performance x Quality
SELECT
    m.process_step,
    s.machine_id,
    ROUND(1.0 * SUM(s.planned_min - s.downtime_min) / SUM(s.planned_min), 3)
        AS availability,
    ROUND(SUM(s.units_total) * m.ideal_cycle_s / 60.0
          / SUM(s.planned_min - s.downtime_min), 3)
        AS performance,
    ROUND(1.0 * SUM(s.units_total - s.units_scrap) / SUM(s.units_total), 3)
        AS quality,
    ROUND(
        (1.0 * SUM(s.planned_min - s.downtime_min) / SUM(s.planned_min))
      * (SUM(s.units_total) * m.ideal_cycle_s / 60.0
          / SUM(s.planned_min - s.downtime_min))
      * (1.0 * SUM(s.units_total - s.units_scrap) / SUM(s.units_total)), 3)
        AS oee
FROM shift_output s
JOIN machines m USING (machine_id)
GROUP BY m.process_step, s.machine_id
ORDER BY oee;

-- name: capacity_by_step
-- Good units per step per day. The step with the lowest output limits
-- the whole line (bottleneck).
SELECT
    m.process_step,
    COUNT(DISTINCT m.machine_id)                       AS machines,
    ROUND(1.0 * SUM(s.units_total - s.units_scrap)
          / COUNT(DISTINCT s.prod_date))               AS good_units_per_day,
    ROUND(1.0 * SUM(s.downtime_min)
          / COUNT(DISTINCT s.prod_date))               AS downtime_min_per_day
FROM shift_output s
JOIN machines m USING (machine_id)
GROUP BY m.process_step
ORDER BY good_units_per_day;

-- name: downtime_pareto
-- Downtime reasons ranked, with cumulative share (Pareto / 80-20)
WITH r AS (
    SELECT reason, SUM(minutes) AS minutes
    FROM downtime_events
    GROUP BY reason
)
SELECT
    reason,
    minutes,
    ROUND(100.0 * minutes / (SELECT SUM(minutes) FROM r), 1) AS share_pct,
    ROUND(100.0 * SUM(minutes) OVER (ORDER BY minutes DESC)
          / (SELECT SUM(minutes) FROM r), 1)                 AS cumulative_pct
FROM r
ORDER BY minutes DESC;

-- name: downtime_by_step_reason
SELECT
    m.process_step,
    d.reason,
    SUM(d.minutes) AS minutes
FROM downtime_events d
JOIN machines m USING (machine_id)
GROUP BY m.process_step, d.reason
ORDER BY m.process_step, minutes DESC;

-- name: scrap_by_shift
SELECT
    m.process_step,
    s.shift,
    ROUND(100.0 * SUM(s.units_scrap) / SUM(s.units_total), 2) AS scrap_pct
FROM shift_output s
JOIN machines m USING (machine_id)
GROUP BY m.process_step, s.shift
ORDER BY m.process_step, s.shift;

-- name: weekly_trend
-- Weekly availability and good output per step, to spot degradation
SELECT
    m.process_step,
    strftime('%Y-%W', s.prod_date)                         AS week,
    ROUND(1.0 * SUM(s.planned_min - s.downtime_min)
          / SUM(s.planned_min), 3)                         AS availability,
    SUM(s.units_total - s.units_scrap)                     AS good_units
FROM shift_output s
JOIN machines m USING (machine_id)
GROUP BY m.process_step, week
ORDER BY m.process_step, week;
