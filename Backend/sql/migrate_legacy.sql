-- Run this if upgrading from the original plain-password schema
USE todo_db;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email VARCHAR(255) NULL AFTER username,
    ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL AFTER email,
    ADD COLUMN IF NOT EXISTS team_id INT NULL,
    MODIFY COLUMN role ENUM('admin', 'manager', 'user') NOT NULL DEFAULT 'user';

UPDATE users SET email = CONCAT(username, '@local.tms') WHERE email IS NULL OR email = '';

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS description TEXT NULL,
    ADD COLUMN IF NOT EXISTS category_id INT NULL,
    ADD COLUMN IF NOT EXISTS due_date DATE NULL,
    ADD COLUMN IF NOT EXISTS reminder_sent TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP NULL;

-- After migrating passwords via init_db.py, drop legacy column:
-- ALTER TABLE users DROP COLUMN password;
