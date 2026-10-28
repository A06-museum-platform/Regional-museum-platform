import { useState } from 'react';
import Modal from '../../components/Modal';
import InterestPicker from '../../components/member/InterestPicker';
import useAsync from '../../hooks/useAsync';
import { listInterestTags } from '../../api/recommendations';
import Button from '../../components/Button';
import FormErrorSummary from '../../components/FormErrorSummary';
import { GALLERIES } from '../../api/constants';
import styles from './StaffContentPage.module.css';

const EMPTY = {
  title: '', summary: '', body: '', gallery: 'main_hall',
  start_date: '', end_date: '', age_min: '', age_max: '', status: 'draft',
};

export default function ExhibitionEditor({ exhibition, onSave, onClose, busy, error }) {
  const [form, setForm] = useState(
    exhibition
      ? {
          ...exhibition,
          start_date: exhibition.start_date ?? '',
          end_date: exhibition.end_date ?? '',
          age_min: exhibition.age_min ?? '',
          age_max: exhibition.age_max ?? '',
        }
      : EMPTY
  );

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const [attempted, setAttempted] = useState(false);
  // Interest tags drive members' recommendations (see recommendation_service).
  const interestTags = useAsync(() => listInterestTags(), []);
  const [tags, setTags] = useState(exhibition?.tags ?? []);
  const [blocking, setBlocking] = useState({});

  const errors = {};
  if (form.title.trim().length <= 2) errors.title = 'Give the exhibition a title.';
  if (form.summary.trim().length <= 10)
    errors.summary = 'Write a one-sentence summary for listing cards.';
  if (!form.start_date) errors.start_date = 'Set the date the exhibition opens.';
  if (form.start_date && form.end_date && form.end_date < form.start_date)
    errors.end_date = 'The closing date needs to be after the opening date.';

  const datesBackwards = Boolean(errors.end_date);

  // Drafts only need a title; everything else is required to publish.
  const draftErrors = {};
  if (errors.title) draftErrors.title = errors.title;
  if (errors.end_date) draftErrors.end_date = errors.end_date;

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
      summary: form.summary.trim(),
      body: form.body.trim(),
      gallery: form.gallery,
      start_date: form.start_date,
      end_date: form.end_date || null,
      age_min: form.age_min === '' ? null : Number(form.age_min),
      age_max: form.age_max === '' ? null : Number(form.age_max),
      status,
      tags,
    });
  };

  return (
    <Modal
      title={exhibition ? 'Edit exhibition' : 'New exhibition'}
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

      <div className="field">
        <label htmlFor="ex-title">Title</label>
        <input
          id="ex-title"
          className={`control ${showError('title') ? 'control--error' : ''}`}
          value={form.title}
          onChange={set('title')}
        />
        {showError('title') && <div className="error-text">{blocking.title}</div>}
      </div>

      <div className="field">
        <label htmlFor="ex-summary">Summary</label>
        <input
          id="ex-summary"
          className={`control ${showError('summary') ? 'control--error' : ''}`}
          value={form.summary}
          onChange={set('summary')}
        />
        {showError('summary')
          ? <div className="error-text">{blocking.summary}</div>
          : <div className="hint">One sentence. This is the line shown on listing cards.</div>}
      </div>

      <div className="field">
        <label htmlFor="ex-body">Full description</label>
        <textarea id="ex-body" className="control" rows={5} value={form.body} onChange={set('body')} />
      </div>

      <div className="field">
        <label htmlFor="ex-gallery">Gallery</label>
        <select id="ex-gallery" className="control" value={form.gallery} onChange={set('gallery')}>
          {Object.entries(GALLERIES).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ex-start">Opens</label>
          <input
            id="ex-start"
            className={`control ${showError('start_date') ? 'control--error' : ''}`}
            type="date"
            value={form.start_date}
            onChange={set('start_date')}
          />
          {showError('start_date') && <div className="error-text">{blocking.start_date}</div>}
        </div>
        <div className="field">
          <label htmlFor="ex-end">Closes</label>
          <input
            id="ex-end"
            className={`control ${datesBackwards ? 'control--error' : ''}`}
            type="date"
            value={form.end_date}
            onChange={set('end_date')}
          />
          {datesBackwards ? (
            <div className="error-text">{errors.end_date}</div>
          ) : (
            <div className="hint">Leave empty for a permanent display.</div>
          )}
        </div>
      </div>

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ex-age-min">Minimum age guidance</label>
          <input id="ex-age-min" className="control" type="number" min="0"
            value={form.age_min} onChange={set('age_min')} placeholder="Any" />
        </div>
        <div className="field">
          <label htmlFor="ex-age-max">Maximum age guidance</label>
          <input id="ex-age-max" className="control" type="number" min="0"
            value={form.age_max} onChange={set('age_max')} placeholder="Any" />
        </div>
      </div>
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
