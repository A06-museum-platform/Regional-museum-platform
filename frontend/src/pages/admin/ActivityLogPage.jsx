import { useState } from 'react';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import { listActivity } from '../../api/activity';
import { USE_MOCKS } from '../../api/client';
import { ACTION_LABELS } from '../../api/mocks/activityLog';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import Button from '../../components/Button';
import styles from './ActivityLogPage.module.css';

const formatWhen = (iso) =>
  new Date(iso).toLocaleString('en-AU', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });

/**
 * Administrator-only audit trail.
 *
 * Read-only by design: there is no edit and no delete, because a log anyone
 * can change is not evidence of anything. Rows are written by the backend as
 * a side effect of the action, never by a client request.
 */
export default function ActivityLogPage() {
  const [q, setQ] = useState('');
  const [action, setAction] = useState('');
  const debouncedQ = useDebouncedValue(q, 300);

  const { data, loading, error, reload } = useAsync(
    () => listActivity({ q: debouncedQ, action }),
    [debouncedQ, action]
  );

  return (
    <div>
      <h1>Activity log <Pill tone="lime">Administrator</Pill></h1>
      <p style={{ color: 'var(--c-muted)' }}>
        Who did what, and why. Read-only.
      </p>

      {USE_MOCKS && (
        <div className={styles.note}>
          <Pill tone="ochre">Mock data</Pill>
          <div>
            Running without the backend: this log is held in memory and resets
            when the page reloads. With the API, every row is written server-side
            as a side effect of the action itself.
          </div>
        </div>
      )}

      <div className={styles.filters}>
        <div className={`field ${styles.searchField}`}>
          <label htmlFor="log-search">Search</label>
          <input id="log-search" className="control" type="search" value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Person, record or reason" />
        </div>
        <div className={`field ${styles.selectField}`}>
          <label htmlFor="log-action">Action</label>
          <select id="log-action" className="control" value={action}
            onChange={(e) => setAction(e.target.value)}>
            <option value="">All actions</option>
            {Object.entries(ACTION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div className={styles.list} style={{ padding: 'var(--s-4)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={44} />)}
          </div>
        </div>
      )}

      {error && (
        <EmptyState title="We could not load the log" body={error.message}>
          <Button onClick={reload}>Try again</Button>
        </EmptyState>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          title="Nothing matches those filters"
          body="Try clearing the search or choosing a different action."
        >
          <Button onClick={() => { setQ(''); setAction(''); }}>Clear filters</Button>
        </EmptyState>
      )}

      {data && data.items.length > 0 && (
        <div className={styles.list}>
          {data.items.map((entry) => (
            <div key={entry.id} className={styles.entry}>
              <div className={styles.when}>{formatWhen(entry.created_at)}</div>
              <div>
                <div className={styles.action}>
                  {ACTION_LABELS[entry.action] ?? entry.action}
                </div>
                <div className={styles.target}>{entry.target}</div>
                <div className={styles.actor}>
                  {entry.actor_name} · {entry.actor_role}
                  {entry.reference && ` · ${entry.reference}`}
                </div>
                {entry.reason && <div className={styles.reason}>{entry.reason}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
