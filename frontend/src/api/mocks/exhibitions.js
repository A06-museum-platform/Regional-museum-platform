/**
 * Exhibition records.
 *
 * An exhibition GROUPS objects; a collection item IS an object. The client
 * asked for both, so they are separate tables with separate pages — do not
 * merge them to save effort.
 *
 * `collection_items.exhibition_id` points at these ids, so changing one here
 * without checking the other leaves orphaned references.
 */

export const EXHIBITIONS = [
  {
    id: 'ex-0001',
    title: 'Colonial Mining & the Overland Telegraph',
    slug: 'colonial-mining-overland-telegraph',
    summary:
      'How copper out of the mid-north paid for the line that connected Adelaide to the world.',
    body:
      'In 1872 South Australia completed one of the great engineering feats of the century, linking Adelaide across 3,200 kilometres of arid desert to Darwin and the global telegraph network. This exhibition follows the copper, the capital and the people who made it possible.',
    gallery: 'telegraph',
    status: 'published',
    start_date: '2026-03-01',
    end_date: '2026-11-15',
    hero_image_url: null,
    age_min: 10,
    age_max: null,
  },
  {
    id: 'ex-0002',
    title: 'Working the Monster Mine',
    slug: 'working-the-monster-mine',
    summary:
      'Cornish miners, Welsh smelters and the town that grew around the largest copper mine in the colony.',
    body:
      'Wage ledgers, tools and photographs from six decades of work at Burra. The exhibition follows a single shift underground, from the change house to the pumping engine that kept the workings dry.',
    gallery: 'monster_mine',
    status: 'published',
    start_date: '2026-02-14',
    end_date: null,
    hero_image_url: null,
    age_min: null,
    age_max: null,
  },
  {
    id: 'ex-0003',
    title: 'Whaling and the Southern Coast',
    slug: 'whaling-and-the-southern-coast',
    summary:
      'The shore stations of Encounter Bay, and what happened when the whales stopped coming.',
    body:
      'Between 1837 and the 1890s shore-based whaling was among the colony\u2019s first export industries. This exhibition sets the economics beside the ecology, and does not flinch from either.',
    gallery: 'encounter_bay',
    status: 'published',
    start_date: '2026-05-02',
    end_date: '2027-02-28',
    hero_image_url: null,
    age_min: 12,
    age_max: null,
  },
  {
    id: 'ex-0004',
    title: 'Kaurna Living Waters and Seasonal Calendars',
    slug: 'kaurna-living-waters',
    summary:
      'Developed with Kaurna community members. Seasonal knowledge along the Karrawirra Parri.',
    body:
      'Freshwater ecosystems, seasonal harvest cycles and language, presented under cultural authority and reviewed with the Kaurna community before display.',
    gallery: 'main_hall',
    status: 'published',
    start_date: '2026-06-01',
    end_date: null,
    hero_image_url: null,
    age_min: null,
    age_max: null,
  },
  {
    id: 'ex-0005',
    title: 'Narrow Gauge: the lines that moved the mid-north',
    slug: 'narrow-gauge-mid-north',
    summary: 'Draft. Rolling stock, timetables and the closure of the branch lines.',
    body:
      'Draft listing held back while the loan agreement for the locomotive plate is finalised.',
    gallery: 'main_hall',
    status: 'draft',
    start_date: '2027-01-15',
    end_date: null,
    hero_image_url: null,
    age_min: null,
    age_max: null,
  },
];

/** Lookup used when resolving `collection_items.exhibition_id`. */
export const exhibitionById = (id) => EXHIBITIONS.find((item) => item.id === id) ?? null;
