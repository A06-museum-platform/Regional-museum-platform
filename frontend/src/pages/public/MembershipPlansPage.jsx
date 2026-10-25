import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { useAuth } from '../../context/AuthContext';
import { listMembershipPlans, getMyMembership, applyForMembership } from '../../api/memberships';
import { coverageLabel } from '../../utils/membership';
import MembershipPlanCard from '../../components/membership/MembershipPlanCard';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from '../../components/membership/Membership.module.css';

/**
 * Membership — choose a plan and apply.
 *
 * Browsing is public; applying needs an account (Flow 6). There are no card
 * fields: applying creates a pending record that an administrator approves
 * from /admin/members, which gives the admin screen something real to act on
 * in the demo.
 */
export default function MembershipPlansPage() {
  const navigate = useNavigate();
  const { user, ready } = useAuth();
  // Visitor and member accounts can hold a membership; staff and admin can't.
  const isMemberAccount = user?.role === 'visitor' || user?.role === 'member';

  const plans = useAsync(listMembershipPlans, []);
  const mine = useAsync(
    () => (ready && isMemberAccount ? getMyMembership(user) : Promise.resolve(null)),
    [ready, user?.id]
  );

  const [selectedKey, setSelectedKey] = useState(null);
  const [children, setChildren] = useState(null); // null = plan's full allowance
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(null);

  const planList = plans.data?.items || [];
  const selected =
    planList.find((plan) => plan.key === selectedKey) ||
    planList.find((plan) => plan.featured) ||
    planList[0] ||
    null;
  const childCount = selected ? Math.min(children ?? selected.max_children, selected.max_children) : 0;
  const existing = mine.data;
  const blocked = existing && (existing.status === 'active' || existing.status === 'pending');

  function choose(plan) {
    setSelectedKey(plan.key);
    setChildren(plan.max_children);
    setError(null);
  }

  async function handleApply() {
    setBusy(true);
    setError(null);
    try {
      const record = await applyForMembership({ plan_id: selected.id, children_covered: childCount }, user);
      setSubmitted(record);
      mine.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Choose a membership</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        Year-round entry to the museum and all four galleries. One membership per account — it
        records how many adults and children it covers.
      </p>

      {plans.loading && (
        <div className={styles.plans}>
          {[0, 1, 2].map((n) => <Skeleton key={n} height={230} />)}
        </div>
      )}

      {plans.error && (
        <EmptyState title="We could not load membership plans" body={plans.error.message}>
          <Button variant="ghost" onClick={plans.reload}>Try again</Button>
        </EmptyState>
      )}

      {planList.length > 0 && (
        <div className={styles.plans}>
          {planList.map((plan) => (
            <MembershipPlanCard key={plan.key} plan={plan} selected={plan.key === selected?.key} onSelect={choose} />
          ))}
        </div>
      )}

      {selected && (submitted ? (
        <div className={styles.success} role="status">
          <h2>Application received</h2>
          <p>
            Your {selected.display_name} membership for {coverageLabel(submitted)} is waiting for
            approval (reference {submitted.member_ref}). No payment has been taken. You can check
            its status on your account page at any time.
          </p>
          <div className={styles.row}>
            <Link to="/account"><Button>Go to my account</Button></Link>
            <Link to="/book"><Button variant="ghost">Book a visit meanwhile</Button></Link>
          </div>
        </div>
      ) : (
        <section className={styles.apply} aria-labelledby="apply-heading">
          <div className={styles.applyHead}>
            <Pill tone="ochre">Prototype</Pill>
            <h2 id="apply-heading">Applications are approved by an administrator</h2>
          </div>
          <p>
            Submitting creates a pending membership record. No payment is taken in this prototype;
            a museum administrator approves it, usually within a few days, and your account becomes a member account straight away.
          </p>

          {!ready || mine.loading ? (
            <Skeleton height={44} width={220} />
          ) : !user ? (
            <>
              <p style={{ fontWeight: 600 }}>Sign in to apply for the {selected.display_name} plan.</p>
              <Button onClick={() => navigate('/signin', { state: { from: '/membership' } })}>
                Sign in to apply
              </Button>
            </>
          ) : !isMemberAccount ? (
            <p style={{ fontWeight: 600, marginBottom: 0 }}>
              You are signed in with a {user.role} account. Staff and administrator accounts do not
              hold memberships — sign in as a visitor to apply.
            </p>
          ) : blocked ? (
            <>
              <p style={{ fontWeight: 600 }}>
                {existing.status === 'active'
                  ? `You already have an active ${existing.plan?.display_name || ''} membership (${existing.member_ref}).`
                  : `Your ${existing.plan?.display_name || ''} application (${existing.member_ref}) is waiting for approval.`}
              </p>
              <Link to="/account"><Button variant="ghost">View my membership</Button></Link>
            </>
          ) : (
            <>
              <div className="field">
                <label htmlFor="children-covered">Who it covers</label>
                {selected.max_children > 0 ? (
                  <select
                    id="children-covered"
                    className="control"
                    value={childCount}
                    onChange={(event) => setChildren(Number(event.target.value))}
                  >
                    {Array.from({ length: selected.max_children + 1 }, (_, n) => (
                      <option key={n} value={n}>
                        {coverageLabel({ adults_covered: selected.adults_covered, children_covered: n })}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div style={{ fontSize: 14 }}>{coverageLabel({ adults_covered: selected.adults_covered, children_covered: 0 })}</div>
                )}
                <div className="hint">Applying as {user.full_name} ({user.email}).</div>
              </div>
              {error && <div className={styles.errorBox} role="alert">{error}</div>}
              <Button onClick={handleApply} disabled={busy}>
                {busy ? 'Submitting…' : `Submit ${selected.display_name} application`}
              </Button>
            </>
          )}
        </section>
      ))}
    </div>
  );
}
