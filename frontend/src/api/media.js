/**
 * Staff media uploads. The shared `request()` helper only speaks JSON,
 * so multipart uploads use fetch directly with the same Bearer scheme
 * and the same ApiError shape as client.js.
 */
import { ApiError, getToken } from './client.js';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const PATHS = {
  'collection-item': 'collection-items',
  'exhibition': 'exhibitions',
  'event': 'events',
};

async function uploadFetch(path, { method = 'GET', form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: form,
    });
  } catch {
    throw new ApiError({
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'We could not reach the server. Check your connection and try again.',
    });
  }

  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError({
      status: response.status,
      code: payload?.code ?? payload?.error?.code ?? 'UNKNOWN',
      message: payload?.detail ?? payload?.error?.message,
    });
  }
  return payload;
}

/**
 * @param {'collection-item'|'exhibition'|'event'} ownerType
 * @param {number|string} ownerId
 * @param {File} file
 * @param {{isPrimary?: boolean, sortOrder?: number}} [options]
 */
export function uploadMedia(ownerType, ownerId, file, options = {}) {
  const segment = PATHS[ownerType];
  if (!segment) throw new Error(`Unknown media owner: ${ownerType}`);
  const params = new URLSearchParams();
  if (options.isPrimary) params.append('is_primary', 'true');
  if (options.sortOrder) params.append('sort_order', String(options.sortOrder));
  const qs = params.toString() ? `?${params}` : '';

  const form = new FormData();
  form.append('file', file);
  return uploadFetch(`/staff/${segment}/${ownerId}/media${qs}`, {
    method: 'POST',
    form,
  });
}

export function listMedia(ownerType, ownerId) {
  const segment = PATHS[ownerType];
  if (!segment) throw new Error(`Unknown media owner: ${ownerType}`);
  return uploadFetch(`/staff/${segment}/${ownerId}/media`);
}

export function deleteMedia(mediaId) {
  return uploadFetch(`/staff/media/${mediaId}`, { method: 'DELETE' });
}
