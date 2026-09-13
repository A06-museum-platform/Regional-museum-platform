import { request, USE_MOCKS, delay, ApiError } from './client';
import { COLLECTION_ITEMS, EXHIBITIONS } from './mocks/collections';

/**
 * Collection search and detail.
 *
 * Contract:
 *   GET /collection-items?q=&gallery=&category=&year_from=&year_to=
 *                        &family_friendly=&page=&page_size=
 *     -> { items, total, page, page_size }
 *   GET /collection-items/{slug}
 *     -> a single item, or 404
 *
 * The mock branch must return the SAME SHAPE as the real branch. When Ray's
 * endpoints land, flipping VITE_USE_MOCKS to false should change nothing that
 * a page can see.
 */

const DEFAULT_PAGE_SIZE = 12;

function filterMocks({ q, gallery, category, year_from, year_to, family_friendly }) {
  const needle = q?.trim().toLowerCase();

  return COLLECTION_ITEMS.filter((item) => {
    if (item.status !== 'published') return false;

    if (needle) {
      const haystack = [
        item.title,
        item.description,
        item.materials,
        item.accession_number,
      ]
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(needle)) return false;
    }

    if (gallery && item.gallery !== gallery) return false;
    if (category && item.category !== category) return false;
    if (year_from && item.year_to && item.year_to < Number(year_from)) return false;
    if (year_to && item.year_from && item.year_from > Number(year_to)) return false;
    if (family_friendly && !item.is_family_friendly) return false;

    return true;
  });
}

export async function searchCollections(params = {}) {
  const page = Number(params.page) || 1;
  const pageSize = Number(params.page_size) || DEFAULT_PAGE_SIZE;

  if (USE_MOCKS) {
    await delay();
    const matched = filterMocks(params);
    const start = (page - 1) * pageSize;
    return {
      items: matched.slice(start, start + pageSize),
      total: matched.length,
      page,
      page_size: pageSize,
    };
  }

  return request('/collection-items', {
    params: { ...params, page, page_size: pageSize },
  });
}

export async function getCollectionItem(slug) {
  if (USE_MOCKS) {
    await delay();
    const item = COLLECTION_ITEMS.find((candidate) => candidate.slug === slug);
    if (!item) {
      throw new ApiError({
        status: 404,
        code: 'NOT_FOUND',
        message: 'That collection item does not exist.',
      });
    }
    // The detail endpoint returns the exhibition nested, not just its id.
    return { ...item, exhibition: EXHIBITIONS[item.exhibition_id] ?? null };
  }

  return request(`/collection-items/${slug}`);
}

/** Total published count, for the "Browse all N items" empty-state button. */
export async function getCollectionCount() {
  if (USE_MOCKS) {
    await delay(0);
    return COLLECTION_ITEMS.filter((item) => item.status === 'published').length;
  }
  const { total } = await request('/collection-items', { params: { page_size: 1 } });
  return total;
}

/**
 * Other items from the same category, for the "See related items" strip.
 *
 * Deliberately reuses the search endpoint rather than adding a
 * /collection-items/{slug}/related route — one fewer endpoint for Ray to
 * build and test, and the filtering logic already exists.
 */
export async function getRelatedItems(item, limit = 3) {
  const { items } = await searchCollections({
    category: item.category,
    page_size: limit + 1,
  });
  return items.filter((candidate) => candidate.id !== item.id).slice(0, limit);
}
