import { useState } from 'react';
import useAsync from '../../hooks/useAsync';
import { getVisitorInformation, saveVisitorInformation } from '../../api/visitInformation';
import Button from '../../components/Button';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import styles from './OpeningHoursPage.module.css';

/**
 * Visitor information — role-permission matrix: "Update visitor information
 * pages" (staff). Edits what /visit shows: address, getting here, contact,
 * about text and the facilities list. Opening hours have their own page.
 *
 * Edited locally and saved in one action, like the opening hours.
 */
export default function VisitorInfoPage() {
  const { data, loading, error, reload } = useAsync(getVisitorInformation, []);

  return (
    <div>
      <h1>Visitor information</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        What the public “Plan your visit” page shows. Opening hours are edited
        separately.
      </p>
      {loading ? (
        <Skeleton height={420} />
      ) : error ? (
        <EmptyState title="We could not load the visitor information" body={error.message}>
          <Button variant="ghost" onClick={reload}>Try again</Button>
        </EmptyState>
      ) : (
        <Editor initial={data} />
      )}
    </div>
  );
}

const FIELDS = [
  ['museum_name', 'Museum name', 'input'],
  ['address', 'Address', 'input'],
  ['phone', 'Phone', 'input'],
  ['email', 'Email', 'input'],
  ['transport', 'Public transport', 'textarea'],
  ['parking', 'Parking', 'textarea'],
  ['about', 'About the museum', 'textarea'],
];

function Editor({ initial }) {
  const [page, setPage] = useState(() => ({
    ...initial,
    facilities: initial.facilities.map((f) => ({ ...f, key: `f-${f.id}` })),
  }));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [savedAt, setSavedAt] = useState(null);

  const change = (changes) => {
    setPage((prev) => ({ ...prev, ...changes }));
    setDirty(true);
    setSavedAt(null);
  };
  const changeFacility = (key, changes) =>
    change({ facilities: page.facilities.map((f) => (f.key === key ? { ...f, ...changes } : f)) });

  const problems = [];
  if (!page.museum_name?.trim()) problems.push('Add the museum name.');
  if (!page.address?.trim()) problems.push('Add the address.');
  if (page.email && !/@[^@\s]+\.[^@\s]+$/.test(page.email)) problems.push('Check the email address.');
  if (page.facilities.some((f) => !f.name.trim())) problems.push('Every facility needs a name.');

  async function save() {
    if (problems.length) return;
    setSaving(true);
    setSaveError(null);
    try {
      const saved = await saveVisitorInformation({
        museum_name: page.museum_name.trim(),
        address: page.address.trim(),
        phone: page.phone?.trim() || null,
        email: page.email?.trim() || null,
        transport: page.transport?.trim() || null,
        parking: page.parking?.trim() || null,
        about: page.about?.trim() || null,
        facilities: page.facilities.map(({ name, description, location, accessibility_info, is_available }) => ({
          name: name.trim(),
          description: description?.trim() || null,
          location: location?.trim() || null,
          accessibility_info: accessibility_info?.trim() || null,
          is_available,
        })),
      });
      setPage({ ...saved, facilities: saved.facilities.map((f) => ({ ...f, key: `f-${f.id}` })) });
      setDirty(false);
      setSavedAt(new Date());
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <section className={styles.panel} aria-labelledby="vi-details">
        <div className={styles.panelHead}>
          <h2 id="vi-details" style={{ margin: 0, fontSize: 'var(--fs-md)' }}>Getting here and contact</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--s-3) var(--s-5)' }}>
          {FIELDS.map(([key, label, kind]) => (
            <div key={key} className="field" style={kind === 'textarea' ? { gridColumn: '1 / -1' } : undefined}>
              <label htmlFor={`vi-${key}`}>{label}</label>
              {kind === 'textarea' ? (
                <textarea id={`vi-${key}`} className="control" rows={3} value={page[key] ?? ''}
                  onChange={(e) => change({ [key]: e.target.value })} />
              ) : (
                <input id={`vi-${key}`} className="control" value={page[key] ?? ''}
                  onChange={(e) => change({ [key]: e.target.value })} />
              )}
            </div>
          ))}
        </div>
      </section>

      <section className={styles.panel} aria-labelledby="vi-facilities">
        <div className={styles.panelHead}>
          <h2 id="vi-facilities" style={{ margin: 0, fontSize: 'var(--fs-md)' }}>Facilities and accessibility</h2>
          <Button size="sm" variant="ghost" onClick={() => change({
            facilities: [...page.facilities, {
              key: `new-${Date.now()}`, name: '', description: '', location: '', accessibility_info: '', is_available: true,
            }],
          })}>
            Add facility
          </Button>
        </div>
        {page.facilities.length === 0 && (
          <p style={{ color: 'var(--c-muted)' }}>No facilities listed yet.</p>
        )}
        {page.facilities.map((facility, index) => (
          <fieldset key={facility.key} style={{
            border: 0, borderTop: '1px solid var(--c-border)', margin: 0, padding: 'var(--s-3) 0',
            display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 'var(--s-3)', alignItems: 'end',
          }}>
            <legend className="sr-only">Facility {index + 1}</legend>
            <div className="field" style={{ margin: 0 }}>
              <label htmlFor={`fac-name-${facility.key}`}>Name</label>
              <input id={`fac-name-${facility.key}`} className="control" value={facility.name}
                onChange={(e) => changeFacility(facility.key, { name: e.target.value })} />
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label htmlFor={`fac-loc-${facility.key}`}>Where</label>
              <input id={`fac-loc-${facility.key}`} className="control" value={facility.location ?? ''}
                onChange={(e) => changeFacility(facility.key, { location: e.target.value })} />
            </div>
            <label style={{ display: 'flex', gap: 'var(--s-2)', alignItems: 'center', minHeight: 'var(--tap-min)', fontSize: 14 }}>
              <input type="checkbox" checked={facility.is_available}
                onChange={(e) => changeFacility(facility.key, { is_available: e.target.checked })} />
              Available
            </label>
            <Button size="sm" variant="ghost" aria-label={`Remove ${facility.name || 'facility'}`}
              onClick={() => change({ facilities: page.facilities.filter((f) => f.key !== facility.key) })}>
              Remove
            </Button>
            <div className="field" style={{ margin: 0, gridColumn: '1 / 3' }}>
              <label htmlFor={`fac-desc-${facility.key}`}>Description</label>
              <input id={`fac-desc-${facility.key}`} className="control" value={facility.description ?? ''}
                onChange={(e) => changeFacility(facility.key, { description: e.target.value })} />
            </div>
            <div className="field" style={{ margin: 0, gridColumn: '3 / 5' }}>
              <label htmlFor={`fac-acc-${facility.key}`}>Accessibility note</label>
              <input id={`fac-acc-${facility.key}`} className="control" value={facility.accessibility_info ?? ''}
                onChange={(e) => changeFacility(facility.key, { accessibility_info: e.target.value })} />
            </div>
          </fieldset>
        ))}
      </section>

      {problems.length > 0 && dirty && (
        <div className={styles.errorBox} role="alert">{problems.join(' ')}</div>
      )}
      {saveError && <div className={styles.errorBox} role="alert">{saveError}</div>}
      <div style={{ display: 'flex', gap: 'var(--s-3)', alignItems: 'center' }}>
        <Button disabled={!dirty || saving || problems.length > 0} onClick={save}>
          {saving ? 'Saving…' : 'Save and publish'}
        </Button>
        {savedAt && <span style={{ color: 'var(--c-ok)', fontSize: 'var(--fs-sm)' }}>Saved — the public page is up to date.</span>}
        {dirty && !savedAt && <span style={{ color: 'var(--c-muted)', fontSize: 'var(--fs-sm)' }}>Unsaved changes</span>}
      </div>
    </>
  );
}
