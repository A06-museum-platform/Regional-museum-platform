-- Audit / activity log (role-permission matrix: "View audit / activity log
-- for all users" -- Admin; a member sees their own activity).
--
-- Rows are written by the backend as a side effect of the action itself,
-- never by a client call: a log the browser can author is not an audit trail.
-- The actor's name and role are copied in, so the entry still reads correctly
-- after the account is renamed, re-roled or deleted.

CREATE TABLE activity_log (
    activity_id INTEGER GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_user_id INTEGER,
    actor_name VARCHAR(200) NOT NULL,
    actor_role VARCHAR(20) NOT NULL,
    action VARCHAR(50) NOT NULL,
    target VARCHAR(300) NOT NULL DEFAULT '',
    reason TEXT,
    reference VARCHAR(40),
    -- Whose record the action was about (the member a booking or approval
    -- belongs to), so a member's "recent activity" includes it.
    subject_user_id INTEGER,

    CONSTRAINT pk_activity_log
        PRIMARY KEY (activity_id),

    CONSTRAINT fk_activity_log_actor
        FOREIGN KEY (actor_user_id)
        REFERENCES user_account (user_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_activity_log_subject
        FOREIGN KEY (subject_user_id)
        REFERENCES user_account (user_id)
        ON DELETE SET NULL
);

CREATE INDEX ix_activity_log_created ON activity_log (created_at DESC);
CREATE INDEX ix_activity_log_actor ON activity_log (actor_user_id);
CREATE INDEX ix_activity_log_subject ON activity_log (subject_user_id);
CREATE INDEX ix_activity_log_action ON activity_log (action);
