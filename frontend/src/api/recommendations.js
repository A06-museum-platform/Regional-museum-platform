import { request, USE_MOCKS, delay } from './client';

/**
 * Interests and recommendations.
 *
 * Contract:
 *   GET /interest-tags                 the vocabulary (public)
 *   GET /me/interests | PUT /me/interests {tags: [slug]}
 *   GET /recommendations?type=&size=   member, staff or admin; 403 for a
 *                                      visitor account
 *
 * Each recommendation says which of the member's interests it matched, so
 * the page can explain itself rather than showing a black-box list.
 */

const MOCK_TAGS = [
  { id: 1, slug: 'mining', label: 'Mining and minerals', description: '' },
  { id: 2, slug: 'telegraph', label: 'Telegraph and communication', description: '' },
  { id: 3, slug: 'maritime', label: 'Sea, ships and whaling', description: '' },
  { id: 8, slug: 'hands_on', label: 'Hands-on activities', description: '' },
];
let mockInterests = ['mining'];

export async function listInterestTags() {
  if (USE_MOCKS) {
    await delay(0);
    return MOCK_TAGS;
  }
  return request('/interest-tags');
}

export async function getMyInterests() {
  if (USE_MOCKS) {
    await delay(0);
    return MOCK_TAGS.filter((t) => mockInterests.includes(t.slug));
  }
  return request('/me/interests');
}

export async function saveMyInterests(slugs) {
  if (USE_MOCKS) {
    await delay();
    mockInterests = slugs;
    return MOCK_TAGS.filter((t) => slugs.includes(t.slug));
  }
  return request('/me/interests', { method: 'PUT', body: { tags: slugs } });
}

export async function getRecommendations({ type = '', size = 6 } = {}) {
  if (USE_MOCKS) {
    await delay();
    return { items: [], total: 0, page: 1, size, interests: [], personalised: false };
  }
  return request('/recommendations', { params: { type, size } });
}

/** Where a recommendation links to. */
export const recommendationHref = (rec) =>
  ({ exhibition: `/exhibitions/${rec.slug}`, event: `/events/${rec.slug}`,
     collection_item: `/collections/${rec.slug}` })[rec.type];
