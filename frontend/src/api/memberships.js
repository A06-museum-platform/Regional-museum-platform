import { request, USE_MOCKS, delay, ApiError } from './client';
import { MEMBERSHIP_PLANS } from './mocks/membershipPlans';
import { MEMBERS } from './mocks/members';
import { recordLocally } from './activity';

/**
 * Visitor-side membership.
 *
 * Contract (section 6, Flow 6):
 *   GET  /membership-plans            public
 *   POST /membership-applications     member — body { plan_id, children_covered }
 * Proposed amendment (see docs/decisions.md, "Booking and membership"):
 *   GET  /memberships/me              member — the caller's own record, or 404
 *
 * Applying never takes payment. It creates a pending record that an
 * administrator approves from /admin/members — which is the same MEMBERS
 * array the admin screen reads, so the whole chain works with mocks.
 */

const planByKey = (key) => MEMBERSHIP_PLANS.find((plan) => plan.key === key);

/** Most relevant record for a user: active, then pending, then the newest. */
function currentRecordFor(userId) {
  const mine = MEMBERS.filter((member) => member.user_id === userId);
  return (
    mine.find((member) => member.status === 'active') ||
    mine.find((member) => member.status === 'pending') ||
    mine.sort((a, b) => new Date(b.applied_at) - new Date(a.applied_at))[0] ||
    null
  );
}

/** Used by the booking mock to decide who may take Member tickets. */
export function activeMembershipFor(userId) {
  const record = currentRecordFor(userId);
  return record?.status === 'active' ? record : null;
}

function withPlan(record) {
  if (!record) return null;
  const plan = planByKey(record.tier);
  return { ...record, plan: plan ? { id: plan.id, display_name: plan.display_name } : null };
}

export async function listMembershipPlans() {
  if (USE_MOCKS) {
    await delay();
    return {
      items: MEMBERSHIP_PLANS.map((plan) => ({ ...plan })),
      total: MEMBERSHIP_PLANS.length,
      page: 1,
      size: MEMBERSHIP_PLANS.length,
    };
  }
  return request('/membership-plans');
}

/** Resolves to null when the caller has never applied. */
export async function getMyMembership(user) {
  if (USE_MOCKS) {
    await delay();
    return withPlan(currentRecordFor(user.id));
  }
  try {
    return await request('/memberships/me');
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

export async function applyForMembership({ plan_id: planId, children_covered: children = 0 }, user) {
  if (USE_MOCKS) {
    await delay();
    const plan = MEMBERSHIP_PLANS.find((candidate) => candidate.id === planId);
    if (!plan) {
      throw new ApiError({ status: 404, code: 'NOT_FOUND', message: 'That membership plan is no longer offered.' });
    }
    if (children < 0 || children > plan.max_children) {
      throw new ApiError({
        status: 400,
        code: 'INVALID_REQUEST',
        message: `The ${plan.display_name} plan covers up to ${plan.max_children} children.`,
      });
    }

    const existing = currentRecordFor(user.id);
    if (existing && (existing.status === 'active' || existing.status === 'pending')) {
      throw new ApiError({
        status: 409,
        code: 'MEMBERSHIP_ACTIVE',
        message:
          existing.status === 'active'
            ? 'You already have an active membership.'
            : 'You already have an application waiting for approval.',
      });
    }

    const record = {
      id: `mb-${String(MEMBERS.length + 1).padStart(4, '0')}`,
      user_id: user.id,
      member_ref: `SA-${9400 + MEMBERS.length}`,
      full_name: user.full_name,
      email: user.email,
      tier: plan.key,
      status: 'pending',
      adults_covered: plan.adults_covered,
      children_covered: plan.max_children === 0 ? 0 : children,
      applied_at: new Date().toISOString(),
      approved_at: null,
      expires_at: null,
      revoked_at: null,
      revoked_reason: null,
    };
    MEMBERS.push(record);
    recordLocally({
      actor: user,
      action: 'member.applied',
      target: `${record.full_name} (${record.member_ref}) — ${plan.display_name}`,
    });
    return withPlan(record);
  }

  return request('/membership-applications', {
    method: 'POST',
    body: { plan_id: planId, children_covered: children },
  });
}
