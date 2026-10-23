import { useState } from 'react';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import { listUsers, updateUser } from '../../api/users';
import { useAuth } from '../../context/AuthContext';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import ConfirmDialog from '../../components/ConfirmDialog';
import styles from './MembersPage.module.css';

/**
 * Administrator-only: who can use the workspace, and at what level
 * (role-permission matrix: "Assign or change user roles").
 *
 * Contract: GET /users?role=staff,admin and PATCH /users/{id} {role, is_active}.
 * The server refuses changes to the administrator's own account (409), so
 * the museum can't be left without an administrator by one careless click;
 * the button for your own row is disabled to say so up front.
 */

const ROLE_LABEL = { staff: 'Staff', admin: 'Administrator', member: 'Member', visitor: 'Visitor' };
const ROLE_SCOPE = {
  staff: 'Exhibitions, collections, events, opening hours, visitor information and bookings',
  admin: 'Everything, including member records, roles and the activity log',
};

const CHANGE_COPY = {
  admin: ['Make administrator', 'They gain access to member records, role management and the activity log.'],
  staff: ['Make staff', 'They can manage content, opening hours and bookings, but not member records or roles.'],
  visitor: ['Remove workspace access', 'They keep their visitor account (and membership, if they have one) but can no longer open the workspace.'],
};

export default function StaffAccountsPage() {
  const { user: actor } = useAuth();
  const team = useAsync(() => listUsers({ role: 'staff,admin' }), []);

  const [q, setQ] = useState('');
  const debouncedQ = useDebouncedValue(q, 300);
  const candidates = useAsync(
    () => (debouncedQ.trim().length >= 2
      ? listUsers({ q: debouncedQ, role: 'visitor,member', size: 8 })
      : Promise.resolve(null)),
    [debouncedQ]
  );

  const [confirming, setConfirming] = useState(null); // { user, changes, title, body, label }
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  function ask(user, changes) {
    if (changes.role) {
      const [label, body] = CHANGE_COPY[changes.role];
      setConfirming({ user, changes, title: `${label}: ${user.display_name}?`, body, label });
    } else {
      setConfirming({
        user, changes,
        title: `${changes.is_active ? 'Re-enable' : 'Disable'} ${user.display_name}’s account?`,
        body: changes.is_active
          ? 'They can sign in again straight away.'
          : 'They are signed out on their next request and can’t sign in until re-enabled. Their records are kept.',
        label: changes.is_active ? 'Re-enable account' : 'Disable account',
      });
    }
  }

  async function apply() {
    setBusy(true);
    setError(null);
    try {
      await updateUser(confirming.user.id, confirming.changes);
      setConfirming(null);
      setQ('');
      team.reload();
    } catch (err) {
      setError(err.message);
      setConfirming(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Staff accounts and roles <Pill tone="lime">Administrator</Pill></h1>
      <p style={{ color: 'var(--c-muted)' }}>
        Staff manage content and bookings. Administrators also manage member records,
        roles and the activity log. Every change is recorded in the activity log.
      </p>

      {error && <div className={styles.errorBox} role="alert">{error}</div>}

      {team.loading ? (
        <div className={styles.tableWrap} style={{ padding: 'var(--s-4)' }}>
          <Skeleton height={40} />
        </div>
      ) : team.error ? (
        <EmptyState title="We could not load the team" body={team.error.message}>
          <Button variant="ghost" onClick={team.reload}>Try again</Button>
        </EmptyState>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr><th>Account</th><th>Role</th><th>Can reach</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {team.data.items.map((account) => {
                const isSelf = account.id === actor?.id;
                return (
                  <tr key={account.id}>
                    <td>
                      <div className={styles.name}>{account.display_name}</div>
                      <div className={styles.meta}>{account.email}</div>
                    </td>
                    <td>
                      <Pill tone={account.role === 'admin' ? 'lime' : 'grey'}>{ROLE_LABEL[account.role]}</Pill>
                    </td>
                    <td style={{ fontSize: 'var(--fs-sm)', color: 'var(--c-muted)', maxWidth: '34ch' }}>
                      {ROLE_SCOPE[account.role]}
                    </td>
                    <td>
                      {account.is_active ? <Pill tone="lime">Active</Pill> : <Pill tone="danger">Disabled</Pill>}
                    </td>
                    <td className={styles.actions}>
                      {isSelf ? (
                        <span className={styles.meta}>This is you</span>
                      ) : (
                        <>
                          <Button size="sm" variant="ghost"
                            onClick={() => ask(account, { role: account.role === 'admin' ? 'staff' : 'admin' })}>
                            {account.role === 'admin' ? 'Make staff' : 'Make administrator'}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => ask(account, { role: 'visitor' })}>
                            Remove access
                          </Button>
                          <Button size="sm" variant={account.is_active ? 'danger' : 'ghost'}
                            onClick={() => ask(account, { is_active: !account.is_active })}>
                            {account.is_active ? 'Disable' : 'Re-enable'}
                          </Button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <section style={{ marginTop: 'var(--s-6)' }} aria-labelledby="add-staff">
        <h2 id="add-staff" style={{ fontSize: 'var(--fs-md)' }}>Add someone to the team</h2>
        <p style={{ color: 'var(--c-muted)', fontSize: 'var(--fs-sm)', maxWidth: '64ch' }}>
          New staff first create an ordinary account on the public site. Find it here by
          name or email and give it staff access.
        </p>
        <div className="field" style={{ maxWidth: 420 }}>
          <label htmlFor="staff-search">Find an account</label>
          <input id="staff-search" className="control" type="search" value={q}
            placeholder="Name or email" onChange={(e) => setQ(e.target.value)} />
        </div>
        {candidates.data && (
          candidates.data.items.length === 0 ? (
            <p className={styles.meta}>No visitor or member account matches “{debouncedQ}”.</p>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table} style={{ minWidth: 0 }}>
                <tbody>
                  {candidates.data.items.map((account) => (
                    <tr key={account.id}>
                      <td>
                        <div className={styles.name}>{account.display_name}</div>
                        <div className={styles.meta}>{account.email} · {ROLE_LABEL[account.role]}</div>
                      </td>
                      <td className={styles.actions}>
                        <Button size="sm" onClick={() => ask(account, { role: 'staff' })}>Make staff</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </section>

      {confirming && (
        <ConfirmDialog
          title={confirming.title}
          body={confirming.body}
          confirmLabel={confirming.label}
          cancelLabel="Leave it"
          busy={busy}
          onCancel={() => setConfirming(null)}
          onConfirm={apply}
        />
      )}
    </div>
  );
}
