import { request, USE_MOCKS, delay, ApiError } from './client';
import { EXHIBITIONS } from './mocks/exhibitions';
import { COLLECTION_ITEMS } from './mocks/collections';

/**
 * Contract:
 *   GET    /exhibitions?q=&gallery=&page=      public, published only
 *   GET    /exhibitions/{slug}                 public
 *   GET    /staff/exhibitions                  staff + admin, includes drafts
 *   POST   /staff/exhibitions
 *   PATCH  /staff/exhibitions/{id}
 *   DELETE /staff/exhibitions/{id}
 */

const slugify = (value) =>
  value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);

/** Objects currently attached to an exhibition. Used for the delete guard. */
export const itemCountFor = (exhibitionId) =>
  COLLECTION_ITEMS.filter((item) => item.exhibition_id === exhibitionId).length;

export async function listExhibitions({ q = '', gallery = '', page = 1, page_size: pageSize = 12 } = {}) {
  if (USE_MOCKS) {
    await delay();
    const needle = q.trim().toLowerCase();
    const matched = EXHIBITIONS.filter((exhibition) => {
      if (exhibition.status !== 'published') return false;
      if (gallery && exhibition.gallery !== gallery) return false;
      if (needle && !`${exhibition.title} ${exhibition.summary}`.toLowerCase().includes(needle)) {
        return false;
      }
      return true;
    });
    const start = (page - 1) * pageSize;
    return {
      items: matched.slice(start, start + pageSize),
      total: matched.length,
      page,
      page_size: pageSize,
    };
  }
  return request('/exhibitions', { params: { q, gallery, page, page_size: pageSize } });
}

export async function getExhibition(slug) {
  if (USE_MOCKS) {
    await delay();
    const exhibition = EXHIBITIONS.find((candidate) => candidate.slug === slug);
    if (!exhibition) {
      throw new ApiError({ status: 404, code: 'NOT_FOUND', message: 'That exhibition does not exist.' });
    }
    return {
      ...exhibition,
      items: COLLECTION_ITEMS.filter(
        (item) => item.exhibition_id === exhibition.id && item.status === 'published'
      ),
    };
  }
  return request(`/exhibitions/${slug}`);
}

export async function listStaffExhibitions({ q = '', status = '', gallery = '' } = {}) {
  if (USE_MOCKS) {
    await delay();
    const needle = q.trim().toLowerCase();
    const matched = EXHIBITIONS.filter((exhibition) => {
      if (status && exhibition.status !== status) return false;
      if (gallery && exhibition.gallery !== gallery) return false;
      if (needle && !`${exhibition.title} ${exhibition.summary}`.toLowerCase().includes(needle)) {
        return false;
      }
      return true;
    }).map((exhibition) => ({ ...exhibition, item_count: itemCountFor(exhibition.id) }));

    return { items: matched, total: matched.length };
  }
  return request('/staff/exhibitions', { params: { q, status, gallery } });
}

export async function createExhibition(payload) {
  if (USE_MOCKS) {
    await delay();
    const exhibition = {
      id: `ex-${String(EXHIBITIONS.length + 1).padStart(4, '0')}`,
      slug: slugify(payload.title),
      hero_image_url: null,
      ...payload,
    };
    EXHIBITIONS.push(exhibition);
    return exhibition;
  }
  return request('/staff/exhibitions', { method: 'POST', body: payload });
}

export async function updateExhibition(id, changes) {
  if (USE_MOCKS) {
    await delay();
    const index = EXHIBITIONS.findIndex((exhibition) => exhibition.id === id);
    if (index === -1) {
      throw new ApiError({ status: 404, code: 'NOT_FOUND', message: 'That exhibition no longer exists.' });
    }
    const next = { ...EXHIBITIONS[index], ...changes };
    if (changes.title && changes.title !== EXHIBITIONS[index].title) {
      next.slug = slugify(changes.title);
    }
    EXHIBITIONS[index] = next;
    return next;
  }
  return request(`/staff/exhibitions/${id}`, { method: 'PATCH', body: changes });
}

/**
 * Refused while objects are still attached.
 *
 * The alternative — silently setting exhibition_id to null on every item —
 * loses curatorial work with no warning. Make the person detach them first so
 * the decision is theirs.
 */
export async function deleteExhibition(id) {
  if (USE_MOCKS) {
    await delay();
    const count = itemCountFor(id);
    if (count > 0) {
      throw new ApiError({
        status: 409,
        code: 'EXHIBITION_HAS_ITEMS',
        message:
          `${count} collection ${count === 1 ? 'object is' : 'objects are'} still attached. ` +
          'Move them to another exhibition first, or unpublish this one instead.',
      });
    }
    const index = EXHIBITIONS.findIndex((exhibition) => exhibition.id === id);
    EXHIBITIONS.splice(index, 1);
    return null;
  }
  return request(`/staff/exhibitions/${id}`, { method: 'DELETE' });
}
