-- Cartwheel smoke report (Lecture 3.3). Not evaluation, just "is the
-- machine on": run these after filling the trace store to check that
-- traces exist, tools fired, and nothing is silently broken.
--
-- These queries target the ClickHouse tables inside self-hosted Langfuse
-- (v3), where `traces` holds one row per trace and `observations` one row
-- per span/generation/event. NOTE: table and column names below may need
-- adjusting to your Langfuse version's ClickHouse schema; check with
-- `SHOW TABLES` and `DESCRIBE traces` first. Attribute-bearing fields are
-- Map(String, String) columns named `metadata`.
--
-- Save the complete report from the Cartwheel root (noninteractive so the
-- committed file is reproducible):
--   docker compose -f observability/docker-compose.yml exec -T clickhouse \
--     clickhouse-client --user clickhouse --password clickhouse -d default \
--     --multiquery < reports/smoke.sql | tee reports/smoke-output.txt
--
-- 1. Traces per scenario (are scenario ids flowing end to end?)
SELECT
    metadata['cartwheel.scenario_id'] AS scenario_id,
    count() AS traces
FROM traces
WHERE metadata['cartwheel.scenario_id'] != ''
GROUP BY scenario_id
ORDER BY traces DESC
LIMIT 50;

-- 2. Traces per user role (are all three roles represented?)
SELECT
    metadata['cartwheel.user_role'] AS role,
    count() AS traces
FROM traces
GROUP BY role
ORDER BY traces DESC;

-- 3. Error count by observation name (anything raising?)
SELECT
    name,
    count() AS errors
FROM observations
WHERE level = 'ERROR'
GROUP BY name
ORDER BY errors DESC
LIMIT 20;

-- 4. Escalation count (how often did the agent punt to a human?)
SELECT count() AS escalations
FROM observations
WHERE name LIKE '%escalate_to_human%';

-- 5. Token and cost totals (the Artifact I arithmetic, observed)
SELECT
    sum(usage_details['input']) AS input_tokens,
    sum(usage_details['output']) AS output_tokens,
    sum(total_cost) AS total_cost
FROM observations
WHERE type = 'GENERATION';

-- 6. Longest traces by span count (candidates for a raw read)
SELECT
    trace_id,
    count() AS spans,
    max(end_time) - min(start_time) AS duration
FROM observations
GROUP BY trace_id
ORDER BY spans DESC
LIMIT 10;

-- 7. Tool-call frequency (which tools does the agent actually use?)
SELECT
    name,
    count() AS calls
FROM observations
WHERE type = 'SPAN'
GROUP BY name
ORDER BY calls DESC
LIMIT 20;

-- 8. Permission-denied count (gold for Module 4; requires the Homework 2
--    attribute to be implemented)
SELECT count() AS permission_denials
FROM observations
WHERE metadata['cartwheel.permission_denied'] = 'true';
