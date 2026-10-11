/**
 * Membership plans, as shown on the revised "Membership — apply" screen.
 *
 * Prices are the reconciled ones from the design review ($65 / $120 / $280);
 * the earlier register screen's $46 family price is gone. `key` matches the
 * `tier` values the admin Members screen already filters on (TIERS in
 * mocks/members.js), so an application made here shows up there unchanged.
 *
 * Coverage is two numbers on the membership record — no household accounts,
 * per the locked scope decision.
 */

export const MEMBERSHIP_PLANS = [
  {
    id: 1,
    key: 'individual',
    display_name: 'Individual',
    price_cents: 6500,
    duration_months: 12,
    adults_covered: 1,
    max_children: 0,
    benefits: ['One adult', 'Unlimited entry', "Members' preview evenings"],
    featured: false,
  },
  {
    id: 2,
    key: 'family',
    display_name: 'Family',
    price_cents: 12000,
    duration_months: 12,
    adults_covered: 2,
    max_children: 3,
    benefits: ['2 adults + up to 3 children', 'Discovery Kit on each visit', 'Priority workshop booking'],
    featured: true,
  },
  {
    id: 3,
    key: 'patron',
    display_name: 'Patron',
    price_cents: 28000,
    duration_months: 12,
    adults_covered: 2,
    max_children: 3,
    benefits: ['All family benefits', 'Guided vault access', 'Named in the annual report'],
    featured: false,
  },
];
