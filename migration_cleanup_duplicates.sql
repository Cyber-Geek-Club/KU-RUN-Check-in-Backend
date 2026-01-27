-- Migration to adding Unique Constraint for Daily Event Participation
-- Created: 2026-01-27
-- Purpose: Remove duplicate records for same user/event/day giving priority to the latest one, and add Unique Constraint.

-- 1. Check for duplicates (Optional - for verification)
-- SELECT user_id, event_id, checkin_date, count(*)
-- FROM event_participations
-- GROUP BY user_id, event_id, checkin_date
-- HAVING count(*) > 1;

BEGIN;

-- 2. Remove duplicates
-- Logic: Keep the record with the HIGHEST ID (latest created)
DELETE FROM event_participations a USING (
    SELECT max(id) as id, user_id, event_id, checkin_date
    FROM event_participations
    GROUP BY user_id, event_id, checkin_date
    HAVING count(*) > 1
) b
WHERE a.user_id = b.user_id 
  AND a.event_id = b.event_id 
  AND a.checkin_date = b.checkin_date 
  AND a.id <> b.id;

-- 3. Add Unique Constraint
ALTER TABLE event_participations
ADD CONSTRAINT uq_event_user_daily_checkin UNIQUE (user_id, event_id, checkin_date);

COMMIT;
