# Core entity relationships

This diagram summarizes the implemented relationships; ordered migrations are
the authoritative DDL. See [schema notes](schema-notes.md) for operations.
Optional relationships are described below rather than hidden by display order.

```mermaid
erDiagram
    user_account ||--o{ user_role : holds
    role ||--o{ user_role : assigns
    user_account ||--o{ membership : applies
    user_account ||--o{ booking : makes
    booking o|--o{ ticket_reservation : groups
    ticket_type ||--o{ ticket_reservation : prices
    user_account ||--o{ event_registration : registers
    event ||--o{ event_registration : receives
    exhibition o|--o{ collection_item : displays
    collection_item o|--o{ media_asset : owns
    exhibition o|--o{ media_asset : owns
    event o|--o{ media_asset : owns
    user_account o|--o{ media_asset : uploads
    user_account ||--o{ user_interest : chooses
    interest_tag ||--o{ user_interest : selected
    interest_tag ||--o{ exhibition_tag : labels
    exhibition ||--o{ exhibition_tag : tagged
    interest_tag ||--o{ event_tag : labels
    event ||--o{ event_tag : tagged
    interest_tag ||--o{ collection_item_tag : labels
    collection_item ||--o{ collection_item_tag : tagged
```

`media_asset` belongs to exactly one of collection item, exhibition or event;
the three optional owner edges are mutually exclusive, enforced by a CHECK.
Its uploader may be null. A collection item may have no exhibition. Legacy
ticket reservations can have no booking; new booking lines are grouped by the
unique booking reference. Media IDs, record IDs and booking references are
separate identifiers. PostgreSQL stores object URLs; Supabase/R2 store bytes.

Reference/operations tables not expanded here include `museum_information`,
`facility`, opening hours/overrides, `activity_log` and `schema_migrations`.
