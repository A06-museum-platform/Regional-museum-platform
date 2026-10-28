import { request, USE_MOCKS, delay } from './client';

/**
 * "Plan your visit" content: address, getting here, contact, about text and
 * facilities / accessibility. Staff edit it on /staff/visit.
 *
 * Contract:
 *   GET /visitor-information
 *   PUT /staff/visitor-information   (the whole page, facilities included)
 */

const MOCK = {
  museum_name: 'SARHN Regional Heritage Museum',
  address: 'Adelaide Cultural Boulevard, North Terrace, Adelaide SA 5000',
  phone: '08 8000 0000',
  email: 'visit@sarhn.org.au',
  transport: 'Tram: Art Gallery / University stop, 40 m to the main entrance.',
  parking: 'Wilson Adelaide Central car park on Frome Street, flat-rate entry.',
  about: 'Four galleries telling the story of copper, telegraph and coastal communities.',
  facilities: [
    { id: 1, name: 'Step-free access', description: 'Ramps and lifts reach every gallery.', location: 'Main entrance', accessibility_info: null, is_available: true },
    { id: 2, name: 'Sensory backpacks', description: 'Headphones, fidget tools and a quiet-route map.', location: 'Front desk', accessibility_info: null, is_available: true },
  ],
};

export async function getVisitorInformation() {
  if (USE_MOCKS) {
    await delay();
    return structuredClone(MOCK);
  }
  return request('/visitor-information');
}

export async function saveVisitorInformation(page) {
  if (USE_MOCKS) {
    await delay();
    Object.assign(MOCK, structuredClone(page));
    return structuredClone(MOCK);
  }
  return request('/staff/visitor-information', { method: 'PUT', body: page });
}
