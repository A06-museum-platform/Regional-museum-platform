import { request, USE_MOCKS, delay, ApiError } from './client';
import { MEMBERS } from './mocks/members';
import { DEMO_USERS } from './mocks/users';
import { recordLocally } from './activity';

/**
 * Administrator-only membership operations.
 *
 * Contract:
 *   GET  /admin/members?q=&status=&tier=&page=
 *   POST /admin/members/{id}/approve
 *   POST /admin/members/{id}/decline
 *   POST /admin/members/{id}/revoke    body { reason }  — reason REQUIRED
 *   POST /admin/members/{id}/restore
 *
 * Staff cannot reach any of these. The client named exactly one administrator
 * power — revoking member access — so the whole surface is admin-only and the
 * role-permission matrix says so.
 */

function deactivateLogin(member, active) {
  const user = DEMO_USERS.find((candidate) => candidate.id === member.user_id);
  if (user) user.is_active = active;
}

export async function listMembers({ q = '', status = '', tier = '' } = {}) {
  if (USE_MOCKS) {
    await delay();
    const needle = q.trim().toLowerCase();
    const matched = MEMBERS.filter((member) => {
      if (status && member.status !== status) return false;
      if (tier && member.tier !== tier) return false;
      if (needle) {
        const haystack =
          `${member.full_name} ${member.email} ${member.member_ref}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    });

    return {
      items: matched,
      total: matched.length,
      counts: {
        pending: MEMBERS.filter((m) => m.status === 'pending').length,
        active: MEMBERS.filter((m) => m.status === 'active').length,
        revoked: MEMBERS.filter((m) => m.status === 'revoked').length,
      },
    };
  }

  return request('/admin/members', { params: { q, status, tier } });
}

function mutate(id, apply) {
  const index = MEMBERS.findIndex((member) => member.id === id);
  if (index === -1) {
    throw new ApiError({ status: 404, code: 'NOT_FOUND', message: 'That member record no longer exists.' });
  }
  MEMBERS[index] = { ...MEMBERS[index], ...apply(MEMBERS[index]) };
  return MEMBERS[index];
}

export async function approveMember(id, actor) {
  if (USE_MOCKS) {
    await delay();
    const member = mutate(id, () => ({
      status: 'active',
      approved_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 365 * 86400000).toISOString(),
    }));
    deactivateLogin(member, true);
    recordLocally({
      actor,
      action: 'member.approved',
      target: `${member.full_name} (${member.member_ref})`,
    });
    return member;
  }
  return request(`/admin/members/${id}/approve`, { method: 'POST' });
}

export async function declineMember(id, reason, actor) {
  if (USE_MOCKS) {
    await delay();
    const member = mutate(id, () => ({ status: 'revoked', revoked_reason: reason || null }));
    recordLocally({
      actor,
      action: 'member.declined',
      target: `${member.full_name} (${member.member_ref})`,
      reason: reason || null,
    });
    return member;
  }
  return request(`/admin/members/${id}/decline`, { method: 'POST', body: { reason } });
}

/**
 * Reason is required, not optional. It is the only record of WHY an account
 * lost access, and "someone revoked it in June" is not an answer a museum can
 * give a member who turns up at the door.
 */
export async function revokeMember(id, reason, actor) {
  if (!reason?.trim()) {
    throw new ApiError({
      status: 422,
      code: 'REASON_REQUIRED',
      message: 'A reason is required so the decision can be explained later.',
    });
  }

  if (USE_MOCKS) {
    await delay();
    const member = mutate(id, () => ({
      status: 'revoked',
      revoked_at: new Date().toISOString(),
      revoked_reason: reason.trim(),
    }));
    deactivateLogin(member, false);
    recordLocally({
      actor,
      action: 'member.revoked',
      target: `${member.full_name} (${member.member_ref})`,
      reason: reason.trim(),
    });
    return member;
  }

  return request(`/admin/members/${id}/revoke`, { method: 'POST', body: { reason } });
}

export async function restoreMember(id, actor) {
  if (USE_MOCKS) {
    await delay();
    const member = mutate(id, () => ({
      status: 'active',
      revoked_at: null,
      revoked_reason: null,
    }));
    deactivateLogin(member, true);
    recordLocally({
      actor,
      action: 'member.restored',
      target: `${member.full_name} (${member.member_ref})`,
    });
    return member;
  }
  return request(`/admin/members/${id}/restore`, { method: 'POST' });
}
