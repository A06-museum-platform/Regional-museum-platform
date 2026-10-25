import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { useAuth } from '../../context/AuthContext';
import { listMembershipPlans, getMyMembership, applyForMembership } from '../../api/memberships';
import { formatPrice } from '../../api/constants';
import { coverageLabel } from '../../utils/membership';
import CardPaymentForm from '../../components/payment/CardPaymentForm';
import { EMPTY_CARD, cardSummary, validateCard } from '../../utils/card';
import FormErrorSummary from '../../components/FormErrorSummary';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import styles from '../../components/membership/Membership.module.css';

/**
 * Membership checkout — pay for the chosen plan, which submits the
 * application. The card form is a demonstration (see CardPaymentForm): any
 * well-formed details are accepted and none are sent to the server. The
 * application then waits for an administrator on /admin/members.
 *
 * URL: /membership/checkout?plan=family&children=2 (survives a refresh).
 */
export default function MembershipCheckoutPage() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const plans = useAsync(listMembershipPlans, []);
  const mine = useAsync(() => getMyMembership(user), [user.id]);

  const [card, setCard] = useState(EMPTY_CARD);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [done, setDone] = useState(null); // { record, paid }

  if (plans.loading || mine.loading) return <Skeleton height={420} />;

  const plan = (plans.data?.items || []).find((p) => p.key === params.get('plan'));
  if (!plan) {
    return (
      <EmptyState title="Choose a membership first" body="We couldn't tell which plan you picked.">
        <Link to="/membership"><Button>See membership plans</Button></Link>
      </EmptyState>
    );
  }

  const requested = Number(params.get('children'));
  const children = Number.isInteger(requested) && requested >= 0
    ? Math.min(requested, plan.max_children) : plan.max_children;
  const coverage = coverageLabel({ adults_covered: plan.adults_covered, children_covered: children });
  const price = formatPrice(plan.price_cents);
  const existing = mine.data;

  if (done) {
    return (
      <div className={styles.success} role="status">
        <h2>Payment received — application submitted</h2>
        <p>
          {done.paid.brand} •••• {done.paid.last4} was charged {price} (demonstration — no money
          was taken). Your {plan.display_name} membership for {coverage} is now <strong>waiting for
          approval</strong> by a museum administrator. Reference {done.record.member_ref}.
        </p>
        <div className={styles.row}>
          <Link to="/account"><Button>Go to my account</Button></Link>
          <Link to="/book"><Button variant="ghost">Book a visit meanwhile</Button></Link>
        </div>
      </div>
    );
  }

  if (existing && (existing.status === 'active' || existing.status === 'pending')) {
    return (
      <EmptyState
        title={existing.status === 'active' ? 'You already have a membership' : 'Your application is already waiting for approval'}
        body={`Reference ${existing.member_ref}. One membership per account.`}
      >
        <Link to="/account"><Button>View my membership</Button></Link>
      </EmptyState>
    );
  }

  async function pay() {
    const next = validateCard(card);
    setErrors(next);
    setSubmitError(null);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      // Only the plan goes to the server — never the card details.
      const record = await applyForMembership({ plan_id: plan.id, children_covered: children }, user);
      setDone({ record, paid: cardSummary(card) });
      setCard(EMPTY_CARD);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const shown = Object.fromEntries(Object.entries(errors).filter(([, v]) => v));

  return (
    <div style={{ maxWidth: 640 }}>
      <h1>Checkout</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        <Link to="/membership">Back to membership plans</Link>
      </p>

      <div className={styles.card} style={{ padding: 'var(--s-4) var(--s-5)' }}>
        <h2 style={{ fontSize: 'var(--fs-md)', marginBottom: 'var(--s-2)' }}>{plan.display_name} membership</h2>
        <div style={{ fontSize: 14, color: 'var(--c-muted)' }}>
          {coverage} · 12 months · for {user.full_name} ({user.email})
        </div>
      </div>

      <CardPaymentForm
        card={card}
        errors={errors}
        amountLabel={`${price} / year`}
        idPrefix="mship"
        onChange={(nextCard, changed) => {
          setCard(nextCard);
          setErrors((prev) => ({ ...prev, [changed]: undefined }));
        }}
      />

      <FormErrorSummary errors={shown} />
      {submitError && <div className={styles.errorBox} role="alert">{submitError}</div>}
      <Button onClick={pay} disabled={busy}>
        {busy ? 'Processing payment…' : `Pay ${price} and apply`}
      </Button>
      <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--c-muted)', marginTop: 'var(--s-3)' }}>
        Your membership starts when an administrator approves the application.
      </p>
    </div>
  );
}
