-- Interests and personalised recommendations (client requirement 3(iv):
-- members see recommendations; proposal: "recommend exhibitions based on
-- visitors' selected interests using an interest-based filtering algorithm").
--
--   interest_tag            the fixed vocabulary (reference data, below)
--   user_interest           which tags an account has chosen
--   exhibition_tag / event_tag / collection_item_tag
--                           which tags describe each piece of content
--
-- Recommendation = content whose tags overlap the member's interests,
-- ranked by how many tags match (app/services/recommendation_service.py).

CREATE TABLE interest_tag (
    tag_id INTEGER GENERATED ALWAYS AS IDENTITY,
    slug VARCHAR(40) NOT NULL,
    label VARCHAR(80) NOT NULL,
    description VARCHAR(200) NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT pk_interest_tag PRIMARY KEY (tag_id),
    CONSTRAINT uq_interest_tag_slug UNIQUE (slug)
);

CREATE TABLE user_interest (
    user_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    CONSTRAINT pk_user_interest PRIMARY KEY (user_id, tag_id),
    CONSTRAINT fk_user_interest_user FOREIGN KEY (user_id)
        REFERENCES user_account (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_interest_tag FOREIGN KEY (tag_id)
        REFERENCES interest_tag (tag_id) ON DELETE CASCADE
);

CREATE TABLE exhibition_tag (
    exhibition_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    CONSTRAINT pk_exhibition_tag PRIMARY KEY (exhibition_id, tag_id),
    CONSTRAINT fk_exhibition_tag_exhibition FOREIGN KEY (exhibition_id)
        REFERENCES exhibition (exhibition_id) ON DELETE CASCADE,
    CONSTRAINT fk_exhibition_tag_tag FOREIGN KEY (tag_id)
        REFERENCES interest_tag (tag_id) ON DELETE CASCADE
);

CREATE TABLE event_tag (
    event_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    CONSTRAINT pk_event_tag PRIMARY KEY (event_id, tag_id),
    CONSTRAINT fk_event_tag_event FOREIGN KEY (event_id)
        REFERENCES event (event_id) ON DELETE CASCADE,
    CONSTRAINT fk_event_tag_tag FOREIGN KEY (tag_id)
        REFERENCES interest_tag (tag_id) ON DELETE CASCADE
);

CREATE TABLE collection_item_tag (
    item_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    CONSTRAINT pk_collection_item_tag PRIMARY KEY (item_id, tag_id),
    CONSTRAINT fk_collection_item_tag_item FOREIGN KEY (item_id)
        REFERENCES collection_item (item_id) ON DELETE CASCADE,
    CONSTRAINT fk_collection_item_tag_tag FOREIGN KEY (tag_id)
        REFERENCES interest_tag (tag_id) ON DELETE CASCADE
);

CREATE INDEX ix_exhibition_tag_tag ON exhibition_tag (tag_id);
CREATE INDEX ix_event_tag_tag ON event_tag (tag_id);
CREATE INDEX ix_collection_item_tag_tag ON collection_item_tag (tag_id);

-- The vocabulary is reference data, so it ships with the schema (staging
-- gets it too). Content is tagged in database/seed/seed.sql and by staff.
INSERT INTO interest_tag (slug, label, description, sort_order) VALUES
('mining', 'Mining and minerals', 'Copper, the Monster Mine and the rocks miners followed underground.', 1),
('telegraph', 'Telegraph and communication', 'Morse code, the Overland Telegraph and how messages crossed a continent.', 2),
('maritime', 'Sea, ships and whaling', 'Encounter Bay, navigation and life on the southern coast.', 3),
('aboriginal_culture', 'Aboriginal culture and Country', 'Kaurna language, seasons and knowledge of the land and waters.', 4),
('railways', 'Railways and transport', 'Narrow-gauge lines, locomotives and moving goods across the mid-north.', 5),
('science', 'Science and technology', 'Engines, batteries, chronometers and how things work.', 6),
('family_history', 'Family history and local people', 'Wage ledgers, photographs and the people behind the objects.', 7),
('hands_on', 'Hands-on activities', 'Workshops and objects that suit curious 10 to 14 year olds.', 8);
