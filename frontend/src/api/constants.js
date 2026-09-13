/**
 * Enum values and their display labels.
 *
 * The KEYS here are the values stored in PostgreSQL and sent over the API —
 * they must match the `gallery` and `category` enums in the data model
 * exactly. The VALUES are what visitors read. Never send a label to the API.
 */

export const GALLERIES = {
  main_hall: 'Main Hall',
  telegraph: 'Telegraph Gallery',
  monster_mine: 'Monster Mine Gallery',
  encounter_bay: 'Encounter Bay Gallery',
};

export const CATEGORIES = {
  mineral: 'Mineral',
  instrument: 'Instrument',
  document: 'Document',
  photograph: 'Photograph',
  machinery: 'Machinery',
};

export const galleryLabel = (key) => GALLERIES[key] ?? key;
export const categoryLabel = (key) => CATEGORIES[key] ?? key;

/** Format integer cents as AUD. The API never sends decimals. */
export const formatPrice = (cents) =>
  new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(
    cents / 100
  );
