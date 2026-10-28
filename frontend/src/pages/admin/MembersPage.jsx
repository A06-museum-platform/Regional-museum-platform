import { useState } from 'react';
import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import {
  listMembers, approveMember, declineMember, revokeMember, restoreMember,
} from '../../api/members';
import { TIERS, MEMBER_STATUSES } from '../../api/mocks/members';
import { useAuth } from '../../context/AuthContext';
import { formatDateShort } from '../../utils/date';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import ConfirmDialog from '../../components/ConfirmDialog';
import styles from './MembersPage.module.css';

const STATUS_TONE = {
  pending: 'ochre',
  active: 'lime',
  revoked: 'danger',
  expired: 'grey',
};

/**
 * Administrator-only member management.
 *
 * This screen exists because the client named exactly one administrator
 * power — revoking member access — and the original wireframes had no screen
 * for it at all. Without it there is nothing to test the administrator role
 * against, and the role-separation evaluation criterion has no artefact.
 */
export default function MembersPage() {
  const { user } = useAuth();

  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [tier, setTier] = useState('');
  const debouncedQ = useDebouncedValue(q, 300);

  const [confirming, setConfirming] = useState(null); // { member, kind }
  const [busy, setBusy] = useState(false);
  const [pageError, setPageError] = useState(null);

  const { data, loading, error, reload } = useAsync(
    () => listMembers({ q: debouncedQ, status, tier }),
    [debouncedQ, status, tier]
  );

  async function run(action) {
    setBusy(true);
    setPageError(null);
    try {
      await action();
      setConfirming(null);
      reload();
    } catch (err) {
      setPageError(err.message);
      setConfirming(null);
    } finally {
      setBusy(false);
    }
  }

  const counts = data?.counts;

  return (
    <div>
      <div className={styles.head}>
        <div>
          <h1>Members <Pill tone="lime">Administrator</Pill></h1>
          <p style={{ color: 'var(--c-muted)', marginBottom: 0 }}>
            Approve applications and revoke access when a membership is misused.
            Museum staff cannot see this screen.
          </p>
        </div>
      </div>

      {pageError && <div className={styles.errorBox}>{pageError}</div>}

      {counts && (
        <div className={styles.counts}>
          {['pending', 'active', 'revoked'].map((key) => (
            <button
              key={key}
              type="button"
              className={`${styles.count} ${status === key ? styles.countActive : ''}`}
              onClick={() => setStatus(status === key ? '' : key)}
            >
              <div className={styles.countValue}>{counts[key]}</div>
              <div className={styles.countLabel}>{MEMBER_STATUSES[key]}</div>
            </button>
          ))}
        </div>
      )}

      <div className={styles.filters}>
        <div className={`field ${styles.searchField}`}>
          <label htmlFor="member-search">Search</label>
          <input id="member-search" className="control" type="search" value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Name, email or member ID" />
        </div>
        <div className={`field ${styles.selectField}`}>
          <label htmlFor="member-status">Status</label>
          <select id="member-status" className="control" value={status}
            onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {Object.entries(MEMBER_STATUSES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div className={`field ${styles.selectField}`}>
          <label htmlFor="member-tier">Tier</label>
          <select id="member-tier" className="control" value={tier}
            onChange={(e) => setTier(e.target.value)}>
            <option value="">All tiers</option>
            {Object.entries(TIERS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div className={styles.tableWrap} style={{ padding: 'var(--s-4)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={40} />)}
          </div>
        </div>
      )}

      {error && (
        <EmptyState title="We could not load the member list" body={error.message}>
          <Button onClick={reload}>Try again</Button>
        </EmptyState>
      )}

      {data && data.items.length === 0 && (
        <EmptyState title="No members match those filters" body="Try a broader search.">
          <Button onClick={() => { setQ(''); setStatus(''); setTier(''); }}>Clear filters</Button>
        </EmptyState>
      )}

      {data && data.items.length > 0 && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Member</th><th>Tier</th><th>Covers</th>
                <th>Joined</th><th>Status</th><th />
              </tr>
            </thead>
            <tbody>
              {data.items.map((member) => (
                <tr key={member.id}>
                  <td>
                    <div className={styles.name}>{member.full_name}</div>
                    <div className={styles.meta}>{member.email} · {member.member_ref}</div>
                    {member.status === 'revoked' && member.revoked_reason && (
                      <div className={styles.revokedReason}>{member.revoked_reason}</div>
                    )}
                  </td>
                  <td>{TIERS[member.tier]}</td>
                  <td>
                    {member.adults_covered} adult{member.adults_covered === 1 ? '' : 's'}
                    {member.children_covered > 0 && ` + ${member.children_covered} children`}
                  </td>
                  <td>
                    {member.approved_at
                      ? formatDateShort(member.approved_at)
                      : <span className={styles.meta}>Applied {formatDateShort(member.applied_at)}</span>}
                  </td>
                  <td><Pill tone={STATUS_TONE[member.status]}>{MEMBER_STATUSES[member.status]}</Pill></td>
                  <td className={styles.actions}>
                    {member.status === 'pending' && (
                      <>
                        <Button size="sm" onClick={() => run(() => approveMember(member.id, user))}>
                          Approve
                        </Button>
                        <Button size="sm" variant="ghost"
                          onClick={() => setConfirming({ member, kind: 'decline' })}>
                          Decline
                        </Button>
                      </>
                    )}
                    {member.status === 'active' && (
                      <Button size="sm" variant="danger"
                        onClick={() => setConfirming({ member, kind: 'revoke' })}>
                        Revoke
                      </Button>
                    )}
                    {(member.status === 'revoked' || member.status === 'expired') && (
                      <Button size="sm" variant="ghost"
                        onClick={() => run(() => restoreMember(member.id, user))}>
                        Restore
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className={styles.chainNote}>
        <Pill tone="ochre">Demo</Pill>
        <div>
          Revoking Eleanor Vance also deactivates her login. Sign out, try her
          account on the sign-in page, and the refusal appears — then check the{' '}
          <Link to="/admin/activity">activity log</Link> for the reason you typed.
          That chain is worth walking through in the Week 10 demonstration.
        </div>
      </div>

      {confirming?.kind === 'revoke' && (
        <ConfirmDialog
          title={`Revoke access for ${confirming.member.full_name}?`}
          body="They are signed out immediately and cannot use the membership to enter or book. Existing bookings are kept, and you can restore access later."
          confirmLabel="Revoke access"
          cancelLabel="Keep access"
          reasonLabel="Reason (recorded in the activity log)"
          reasonRequired
          busy={busy}
          onCancel={() => setConfirming(null)}
          onConfirm={(reason) => run(() => revokeMember(confirming.member.id, reason, user))}
        />
      )}

      {confirming?.kind === 'decline' && (
        <ConfirmDialog
          title={`Decline ${confirming.member.full_name}'s application?`}
          body="The application is closed. They can apply again later."
          confirmLabel="Decline application"
          cancelLabel="Keep it open"
          reasonLabel="Reason"
          busy={busy}
          onCancel={() => setConfirming(null)}
          onConfirm={(reason) => run(() => declineMember(confirming.member.id, reason, user))}
        />
      )}
    </div>
  );
}
