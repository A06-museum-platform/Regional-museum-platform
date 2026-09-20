import { useEffect, useState } from 'react';
import useAsync from '../../hooks/useAsync';
import { getOpeningHours, saveOpeningHours, DAY_NAMES } from '../../api/openingHours';
import Button from '../../components/Button';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import styles from './OpeningHoursPage.module.css';

/**
 * Opening hours — client requirement 4(a): staff update opening hours.
 *
 * The client said hours change seasonally, so this supports a weekly pattern
 * plus dated overrides. An override always wins for its date.
 *
 * Everything is edited locally and saved in one action. Autosaving a
 * timetable field by field is a good way to publish 09:0 to the public site
 * while someone is still typing.
 */
export default function OpeningHoursPage() {
  const { data, loading, error } = useAsync(getOpeningHours, []);

  const [weekly, setWeekly] = useState([]);
  const [overrides, setOverrides] = useState([]);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    if (!data) return;
    setWeekly(data.weekly);
    setOverrides(data.overrides);
  }, [data]);

  const patch = (setter) => (id, changes) => {
    setter((rows) => rows.map((row) => (row.id === id ? { ...row, ...changes } : row)));
    setDirty(true);
    setSavedAt(null);
  };

  const patchWeekly = patch(setWeekly);
  const patchOverride = patch(setOverrides);

  function addOverride() {
    setOverrides((rows) => [
      ...rows,
      {
        id: `oh-new-${Date.now()}`,
        specific_date: '',
        opens_at: '10:00',
        closes_at: '16:00',
        is_closed: false,
        note: '',
      },
    ]);
    setDirty(true);
  }

  function removeOverride(id) {
    setOverrides((rows) => rows.filter((row) => row.id !== id));
    setDirty(true);
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await saveOpeningHours({ weekly, overrides });
      setDirty(false);
      setSavedAt(new Date());
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div>
        <h1>Opening hours</h1>
        <div className={styles.panel}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            {Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} height={38} />)}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState title="We could not load the timetable" body={error.message}>
        <Button onClick={() => window.location.reload()}>Try again</Button>
      </EmptyState>
    );
  }

  const renderTimes = (row, onPatch) => (
    <>
      <input
        className={`control ${row.is_closed ? styles.dimmed : ''}`}
        type="time"
        value={row.opens_at ?? ''}
        disabled={row.is_closed}
        onChange={(e) => onPatch(row.id, { opens_at: e.target.value })}
        aria-label="Opening time"
      />
      <input
        className={`control ${row.is_closed ? styles.dimmed : ''}`}
        type="time"
        value={row.closes_at ?? ''}
        disabled={row.is_closed}
        onChange={(e) => onPatch(row.id, { closes_at: e.target.value })}
        aria-label="Closing time"
      />
      <label className={styles.closedToggle}>
        <input
          type="checkbox"
          checked={row.is_closed}
          onChange={(e) =>
            onPatch(row.id, {
              is_closed: e.target.checked,
              opens_at: e.target.checked ? null : row.opens_at || '10:00',
              closes_at: e.target.checked ? null : row.closes_at || '16:00',
            })
          }
        />
        Closed
      </label>
    </>
  );

  return (
    <div>
      <h1>Opening hours</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        The weekly pattern applies all year. Add a dated exception for a public
        holiday or a seasonal change — the exception always wins for its date.
      </p>

      {saveError && <div className={styles.errorBox}>{saveError}</div>}

      <section className={styles.panel}>
        <div className={styles.panelHead}><h2 style={{ margin: 0 }}>Weekly pattern</h2></div>

        <div className={styles.rowHead}>
          <div>Day</div><div>Opens</div><div>Closes</div><div /><div>Note shown to visitors</div><div />
        </div>

        {weekly.map((row) => (
          <div key={row.id} className={styles.row}>
            <div className={styles.day}>{DAY_NAMES[row.day_of_week]}</div>
            {renderTimes(row, patchWeekly)}
            <input
              className="control"
              value={row.note ?? ''}
              placeholder="Optional"
              onChange={(e) => patchWeekly(row.id, { note: e.target.value })}
              aria-label={`Note for ${DAY_NAMES[row.day_of_week]}`}
            />
            <div />
          </div>
        ))}
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 style={{ margin: 0 }}>Dated exceptions</h2>
          <Button size="sm" variant="ghost" onClick={addOverride}>Add an exception</Button>
        </div>

        {overrides.length === 0 && (
          <p style={{ color: 'var(--c-muted)', fontSize: 14, marginBottom: 0 }}>
            No exceptions set. The weekly pattern applies every day.
          </p>
        )}

        {overrides.length > 0 && (
          <div className={styles.rowHead}>
            <div>Date</div><div>Opens</div><div>Closes</div><div /><div>Note</div><div />
          </div>
        )}

        {overrides.map((row) => (
          <div key={row.id} className={styles.row}>
            <input
              className="control"
              type="date"
              value={row.specific_date ?? ''}
              onChange={(e) => patchOverride(row.id, { specific_date: e.target.value })}
              aria-label="Exception date"
            />
            {renderTimes(row, patchOverride)}
            <input
              className="control"
              value={row.note ?? ''}
              placeholder="e.g. Public holiday"
              onChange={(e) => patchOverride(row.id, { note: e.target.value })}
              aria-label="Exception note"
            />
            <Button size="sm" variant="ghost" onClick={() => removeOverride(row.id)}>Remove</Button>
          </div>
        ))}
      </section>

      <div className={styles.bar}>
        <div>
          {dirty && <span style={{ color: 'var(--c-muted)', fontSize: 14 }}>Unsaved changes</span>}
          {!dirty && savedAt && (
            <span className={styles.saved}>
              Saved at {savedAt.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
        <Button disabled={!dirty || saving} onClick={save}>
          {saving ? 'Saving…' : 'Save opening hours'}
        </Button>
      </div>
    </div>
  );
}
