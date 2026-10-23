import { request, USE_MOCKS, delay } from './client';
import { DEMO_USERS } from './mocks/users';

/**
 * Administrator account management (role-permission matrix: "Assign or
 * change user roles", "Revoke member access").
 *
 * Contract (docs/api-contract.md section 9):
 *   GET   /users?q=&role=staff,admin&size=
 *   PATCH /users/{id}   body any of { role, is_active }
 * An administrator can't change their own role or access (409).
 */

const toUser = ({ full_name, ...user }) => {
  const safe = { ...user, display_name: full_name };
  delete safe.password;
  return safe;
};

export async function listUsers({ q = '', role = '', size = 50 } = {}) {
  if (USE_MOCKS) {
    await delay();
    const roles = role ? role.split(',') : null;
    const needle = q.trim().toLowerCase();
    const items = DEMO_USERS.filter((u) => (!roles || roles.includes(u.role))
      && (!needle || `${u.full_name} ${u.email}`.toLowerCase().includes(needle))).map(toUser);
    return { items, total: items.length, page: 1, size };
  }
  return request('/users', { params: { q, role, size } });
}

export async function updateUser(id, changes) {
  if (USE_MOCKS) {
    await delay();
    const user = DEMO_USERS.find((u) => u.id === id);
    Object.assign(user, changes);
    return toUser(user);
  }
  return request(`/users/${id}`, { method: 'PATCH', body: changes });
}
