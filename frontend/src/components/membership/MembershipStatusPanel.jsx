import { Link } from 'react-router-dom';
import { formatDate } from '../../utils/date';
import { coverageLabel } from '../../utils/membership';
import Button from '../Button';
import Pill from '../Pill';
import styles from './Membership.module.css';

const STATUS_PILL = {
  active: ['lime', 'Active'],
  pending: ['ochre', 'Pending approval'],
  revoked: ['danger', 'Revoked'],
  expired: ['grey', 'Expired'],
};

/**
 * The member's own record: tier, reference, who it covers and until when.
 * One record per account, per the locked scope decision — the coverage line
 * ("2 adults + 3 children") is the whole of the household model.
 */
export default function MembershipStatusPanel({ membership }) {
  if (!membership) {
    return (
      <div className={`${styles.statusNote} ${styles.statusPending}`}>
        <h3>You are not a member yet</h3>
        <p>Members visit free all year, get preview evenings and book workshops first.</p>
        <Link to="/membership"><Button size="sm">Choose a membership</Button></Link>
      </div>
    );
  }

  const [tone, label] = STATUS_PILL[membership.status] || ['grey', membership.status];
  const tierName = membership.plan?.display_name || membership.tier;

  if (membership.status === 'pending') {
    return (
      <div className={`${styles.statusNote} ${styles.statusPending}`} role="status">
        <div className={styles.row} style={{ marginBottom: 'var(--s-2)' }}>
          <Pill tone="ochre">{label}</Pill>
          <span className="hint" style={{ margin: 0 }}>Reference {membership.member_ref}</span>
        </div>
        <h3>Your {tierName} membership application is with our team</h3>
        <p>
          Applied {formatDate(membership.applied_at)} for {coverageLabel(membership)}. A staff member
          reviews each application; you will see it here as soon as it is approved. No payment
          has been taken.
        </p>
      </div>
    );
  }

  if (membership.status === 'revoked' || membership.status === 'expired') {
    return (
      <div className={`${styles.statusNote} ${styles.statusBad}`} role="status">
        <div className={styles.row} style={{ marginBottom: 'var(--s-2)' }}>
          <Pill tone={tone}>{label}</Pill>
          <span className="hint" style={{ margin: 0 }}>Reference {membership.member_ref}</span>
        </div>
        <h3>Your {tierName} membership is no longer active</h3>
        <p>
          {membership.status === 'expired'
            ? `It ended on ${formatDate(membership.expires_at)}.`
            : 'Access was withdrawn by the museum. Contact the front desk if you think this is a mistake.'}
        </p>
        {membership.status === 'expired' && (
          <Link to="/membership"><Button size="sm">Renew membership</Button></Link>
        )}
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <div className={styles.cardTop}>
        <div>
          <div className={styles.cardEyebrow}>Membership</div>
          <div className={styles.cardTier}>{tierName}</div>
          <div className={styles.cardRef}>{membership.member_ref}</div>
        </div>
        <div><Pill tone={tone}>{label}</Pill></div>
      </div>
      <div className={styles.cardBody}>
        <table className={styles.facts}>
          <tbody>
            <tr><th scope="row">Name</th><td>{membership.full_name}</td></tr>
            <tr><th scope="row">Covers</th><td>{coverageLabel(membership)}</td></tr>
            <tr><th scope="row">Member since</th><td>{formatDate(membership.approved_at || membership.applied_at)}</td></tr>
            <tr><th scope="row">Valid until</th><td>{membership.expires_at ? formatDate(membership.expires_at) : '—'}</td></tr>
          </tbody>
        </table>
        <div className={styles.row} style={{ marginTop: 'var(--s-4)' }}>
          <Link to="/book"><Button size="sm">Book a free member visit</Button></Link>
          <span className="hint" style={{ margin: 0 }}>Member tickets cover everyone on this membership.</span>
        </div>
      </div>
    </div>
  );
}
