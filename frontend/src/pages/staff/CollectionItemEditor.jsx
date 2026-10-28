import { useState } from 'react';
import Modal from '../../components/Modal';
import InterestPicker from '../../components/member/InterestPicker';
import useAsync from '../../hooks/useAsync';
import { listInterestTags } from '../../api/recommendations';
import Button from '../../components/Button';
import FormErrorSummary from '../../components/FormErrorSummary';
import { GALLERIES, CATEGORIES } from '../../api/constants';
import styles from './StaffContentPage.module.css';

/**
 * Every field here has a column in the `collection_items` table and a row on
 * the public item page. If you add a field, all three have to move together:
 * database, editor, visitor page. That is the contract the wireframe review
 * called out, made concrete.
 */

const EMPTY = {
  title: '', accession_number: '', description: '',
  category: 'mineral', gallery: 'main_hall',
  period_text: '', year_from: '', year_to: '', materials: '',
  exhibition_id: '', is_family_friendly: false, status: 'draft',
};

export default function CollectionItemEditor({ item, exhibitions, onSave, onClose, busy, error }) {
  const [form, setForm] = useState(
    item
      ? {
          ...item,
          year_from: item.year_from ?? '',
          year_to: item.year_to ?? '',
          exhibition_id: item.exhibition_id ?? '',
        }
      : EMPTY
  );

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const [attempted, setAttempted] = useState(false);
  // Interest tags drive members' recommendations (see recommendation_service).
  const interestTags = useAsync(() => listInterestTags(), []);
  const [tags, setTags] = useState(item?.tags ?? []);

  // One object describing everything that is wrong right now. Rendered as a
  // summary above the buttons and beside the individual fields, but only
  // after the first submit — telling someone their title is too short before
  // they have finished typing it is just nagging.
  const errors = {};
  if (form.title.trim().length <= 2) errors.title = 'Give the object a title.';
  if (form.accession_number.trim().length <= 2)
    errors.accession_number = 'An accession number is required.';
  if (form.description.trim().length <= 10)
    errors.description = 'Write at least a sentence of description.';
  if (!form.period_text.trim())
    errors.period_text = 'Add the date as it should appear to visitors, such as “c. 1848”.';
  if (form.year_from && form.year_to && Number(form.year_to) < Number(form.year_from))
    errors.year_to = 'The later year cannot be before the earlier one.';

  const yearsBackwards = Boolean(errors.year_to);

  // A draft is work in progress, so it only needs a title. Everything else is
  // required to PUBLISH. Forcing a complete record before anything can be
  // saved is what makes people keep notes in a separate document.
  const draftErrors = {};
  if (form.title.trim().length <= 2) draftErrors.title = errors.title;
  if (errors.year_to) draftErrors.year_to = errors.year_to;

  const [blocking, setBlocking] = useState({});
  const showError = (key) => (attempted ? blocking[key] : null);

  const save = (status) => {
    const check = status === 'draft' ? draftErrors : errors;
    if (Object.keys(check).length > 0) {
      setBlocking(check);
      setAttempted(true);
      return;
    }
    onSave({
      title: form.title.trim(),
      accession_number: form.accession_number.trim(),
      description: form.description.trim(),
      category: form.category,
      gallery: form.gallery,
      period_text: form.period_text.trim(),
      year_from: form.year_from === '' ? null : Number(form.year_from),
      year_to: form.year_to === '' ? null : Number(form.year_to),
      materials: form.materials.trim(),
      exhibition_id: form.exhibition_id || null,
      is_family_friendly: Boolean(form.is_family_friendly),
      status,
      tags,
    });
  };

  return (
    <Modal
      title={item ? 'Edit object' : 'New object'}
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="ghost" disabled={busy} onClick={() => save('draft')}>
            Save as draft
          </Button>
          <Button disabled={busy} onClick={() => save('published')}>
            {busy ? 'Saving…' : 'Publish'}
          </Button>
        </>
      }
    >
      {error && <div className={styles.errorBox}>{error}</div>}
      {attempted && <FormErrorSummary errors={blocking} />}

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ci-title">Title</label>
          <input
            id="ci-title"
            className={`control ${showError('title') ? 'control--error' : ''}`}
            value={form.title}
            onChange={set('title')}
          />
          {showError('title') && <div className="error-text">{blocking.title}</div>}
        </div>
        <div className="field">
          <label htmlFor="ci-accession">Accession number</label>
          <input
            id="ci-accession"
            className={`control ${showError('accession_number') ? 'control--error' : ''}`}
            value={form.accession_number}
            onChange={set('accession_number')}
          />
          {showError('accession_number')
            ? <div className="error-text">{blocking.accession_number}</div>
            : <div className="hint">Must be unique across the whole collection.</div>}
        </div>
      </div>

      <div className="field">
        <label htmlFor="ci-description">Description</label>
        <textarea
          id="ci-description"
          className={`control ${showError('description') ? 'control--error' : ''}`}
          rows={4}
          value={form.description}
          onChange={set('description')}
        />
        {showError('description')
          ? <div className="error-text">{blocking.description}</div>
          : <div className="hint">
              Written for a visitor standing in front of the object, not for a catalogue.
            </div>}
      </div>

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ci-category">Category</label>
          <select id="ci-category" className="control" value={form.category} onChange={set('category')}>
            {Object.entries(CATEGORIES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ci-gallery">On display at</label>
          <select id="ci-gallery" className="control" value={form.gallery} onChange={set('gallery')}>
            {Object.entries(GALLERIES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="field">
        <label htmlFor="ci-period">Date, as shown to visitors</label>
        <input
          id="ci-period"
          className={`control ${showError('period_text') ? 'control--error' : ''}`}
          value={form.period_text}
          onChange={set('period_text')}
          placeholder="c. 1848"
        />
        {showError('period_text') && <div className="error-text">{blocking.period_text}</div>}
        <div className="hint">
          Free text, because &ldquo;c. 1848&rdquo; and &ldquo;1871&ndash;1872&rdquo; both need to be
          sayable. The numeric years below are what search filters on.
        </div>
      </div>

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ci-year-from">Year from</label>
          <input id="ci-year-from" className="control" type="number"
            value={form.year_from} onChange={set('year_from')} placeholder="1845" />
        </div>
        <div className="field">
          <label htmlFor="ci-year-to">Year to</label>
          <input
            id="ci-year-to"
            className={`control ${yearsBackwards ? 'control--error' : ''}`}
            type="number"
            value={form.year_to}
            onChange={set('year_to')}
            placeholder="1850"
          />
          {yearsBackwards && <div className="error-text">{errors.year_to}</div>}
        </div>
      </div>

      <div className="field">
        <label htmlFor="ci-materials">Materials</label>
        <input id="ci-materials" className="control" value={form.materials} onChange={set('materials')} />
      </div>

      <div className="field">
        <label htmlFor="ci-exhibition">Part of</label>
        <select id="ci-exhibition" className="control"
          value={form.exhibition_id} onChange={set('exhibition_id')}>
          <option value="">Not in an exhibition</option>
          {exhibitions.map((exhibition) => (
            <option key={exhibition.id} value={exhibition.id}>
              {exhibition.title}
              {exhibition.status === 'draft' ? ' (draft)' : ''}
            </option>
          ))}
        </select>
      </div>

      <label className="field" style={{ display: 'flex', gap: 'var(--s-2)', alignItems: 'center' }}>
        <input
          type="checkbox"
          checked={form.is_family_friendly}
          onChange={(e) => setForm((prev) => ({ ...prev, is_family_friendly: e.target.checked }))}
        />
        <span style={{ fontSize: 14 }}>
          Suitable for ages 10&ndash;14
          <span className="hint" style={{ marginTop: 0 }}>
            Drives the family filter on the public collection search.
          </span>
        </span>
      </label>
      {interestTags.data && (
        <InterestPicker
          tags={interestTags.data}
          selected={tags}
          onChange={setTags}
          label="Interest tags — members who chose these see it in their recommendations"
        />
      )}
    </Modal>
  );
}
