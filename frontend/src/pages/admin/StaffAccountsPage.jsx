import { useState } from 'react';
import useAsync from '../../hooks/useAsync';
import { DEMO_USERS } from '../../api/mocks/users';
import { USE_MOCKS, delay, request } from '../../api/client';
import { recordLocally } from '../../api/activity';
import { useAuth } from '../../context/AuthContext';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import ConfirmDialog from '../../components/ConfirmDialog';
import styles from './MembersPage.module.css';

/**
 * Administrator-only: who can sign in to the workspace, and at what level.
 *
 * Contract:
 *   GET   /admin/staff-accounts
 *   PATCH /admin/staff-accounts/{id}   body { role }
 */

async function listStaffAccounts() {
  if (USE_MOCKS) {
    await delay();
    return DEMO_USERS.filter((user) => user.role !== 'member').map(
      ({ password: _ignored, ...user }) => user
    );
  }
  return request('/admin/staff-accounts');
}

async function changeRole(id, role, actor) {
  if (USE_MOCKS) {
    await delay();
    const user = DEMO_USERS.find((candidate) => candidate.id === id);
    user.role = role;
    recordLocally({
      actor,
      action: 'role.changed',
      target: `${user.full_name} → ${role}`,
    });
    return user;
  }
  return request(`/admin/staff-accounts/${id}`, { method: 'PATCH', body: { role } });
}

const ROLE_LABEL = { staff: 'Staff', admin: 'Administrator' };

const ROLE_SCOPE = {
  staff: 'Exhibitions, collections, events and opening hours',
  admin: 'Everything, including member records and this screen',
};

export default function StaffAccountsPage() {
  const { user: actor } = useAuth();
  const { data, loading, reload } = useAsync(listStaffAccounts, []);
  const [confirming, setConfirming] = useState(null);
  const [busy, setBusy] = useState(false);

  async function apply() {
    setBusy(true);
    try {
      await changeRole(confirming.user.id, confirming.nextRole, actor);
      setConfirming(null);
      reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Staff accounts and roles <Pill tone="lime">Administrator</Pill></h1>
      <p style={{ color: 'var(--c-muted)' }}>
        Staff manage content. Administrators additionally manage member records,
        roles and the activity log.
      </p>

      {loading && (
        <div className={styles.tableWrap} style={{ padding: 'var(--s-4)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            {Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} height={40} />)}
          </div>
        </div>
      )}

      {data && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr><th>Account</th><th>Role</th><th>Can reach</th><th /></tr>
            </thead>
            <tbody>
              {data.map((account) => {
                const isSelf = account.id === actor?.id;
                const nextRole = account.role === 'admin' ? 'staff' : 'admin';
                return (
                  <tr key={account.id}>
                    <td>
                      <div className={styles.name}>{account.full_name}</div>
                      <div className={styles.meta}>{account.email}</div>
                    </td>
                    <td>
                      <Pill tone={account.role === 'admin' ? 'lime' : 'grey'}>
                        {ROLE_LABEL[account.role]}
                      </Pill>
                    </td>
                    <td style={{ fontSize: 'var(--fs-sm)', color: 'var(--c-muted)', maxWidth: '34ch' }}>
                      {ROLE_SCOPE[account.role]}
                    </td>
                    <td className={styles.actions}>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={isSelf}
                        title={isSelf ? 'You cannot change your own role' : undefined}
                        onClick={() => setConfirming({ user: account, nextRole })}
                      >
                        {isSelf ? 'This is you' : `Make ${ROLE_LABEL[nextRole].toLowerCase()}`}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/*
        An administrator cannot demote themselves. Without this it takes one
        careless click to leave the museum with no administrator at all, and
        no way back in through the interface.
      */}

      {confirming && (
        <ConfirmDialog
          title={`Change ${confirming.user.full_name} to ${ROLE_LABEL[confirming.nextRole]}?`}
          body={
            confirming.nextRole === 'admin'
              ? 'They gain access to member records, role management and the activity log.'
              : 'They lose access to member records, role management and the activity log. Content management is unaffected.'
          }
          confirmLabel="Change role"
          cancelLabel="Leave it"
          busy={busy}
          onCancel={() => setConfirming(null)}
          onConfirm={apply}
        />
      )}
    </div>
  );
}
