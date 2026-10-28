import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import MediaUploader from '../../components/MediaUploader';
import useAsync from '../../hooks/useAsync';
import { listStaffExhibitions } from '../../api/exhibitions';
import { listStaffCollectionItems } from '../../api/collections';
import { listStaffEvents } from '../../api/events';

const TYPES = {
  'collection-item': { label: 'Collection object', load: listStaffCollectionItems },
  exhibition: { label: 'Exhibition', load: listStaffExhibitions },
  event: { label: 'Event', load: listStaffEvents },
};

export default function StaffMediaPage() {
  const [params, setParams] = useSearchParams();
  const ownerType = Object.hasOwn(TYPES, params.get('type')) ? params.get('type') : 'collection-item';
  const recordId = params.get('id') || '';
  const [busy, setBusy] = useState(false);
  const { data, loading, error, reload } = useAsync(() => TYPES[ownerType].load(), [ownerType]);
  // Never label a previous type's results as current while its replacement loads.
  const records = loading || error ? [] : [...(data?.items ?? [])].sort((a, b) => a.title.localeCompare(b.title));
  const selected = records.find(record => String(record.id) === recordId);
  return (
    <div>
      <h1>Media library</h1>
      <p>Choose a record by title. Images are uploaded to the selected record immediately.</p>
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'end', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div className="field">
          <label htmlFor="media-type">Record type</label>
          <select id="media-type" className="control" value={ownerType} disabled={busy}
            onChange={event => setParams({ type: event.target.value })}>
            {Object.entries(TYPES).map(([value, type]) => <option key={value} value={value}>{type.label}</option>)}
          </select>
        </div>
        <div className="field" style={{ maxWidth: '100%' }}>
          <label htmlFor="media-record">Record</label>
          <select id="media-record" className="control" value={selected ? recordId : ''} disabled={busy || loading || Boolean(error)}
            onChange={event => setParams({ type: ownerType, id: event.target.value })} style={{ maxWidth: '100%' }}>
            <option value="">{loading ? 'Loading records…' : 'Choose a record…'}</option>
            {records.map(record => <option key={record.id} value={String(record.id)}>
              {record.title} — ID {record.id} ({record.status === 'published' ? 'Published' : 'Draft'})
            </option>)}
          </select>
        </div>
      </div>
      {loading && <p role="status">Loading records…</p>}
      {error && <div role="alert"><p>{error.message}</p><button onClick={reload}>Retry loading records</button></div>}
      {!loading && !error && !records.length && <p>No records of this type are available.</p>}
      {!loading && !error && recordId && !selected && <p role="alert">This record is no longer available. Choose another record.</p>}
      {selected && <section aria-label="Selected record media">
        <h2>Images for {selected.title}</h2>
        <p>{TYPES[ownerType].label} record ID: <strong>{selected.id}</strong> · {selected.status === 'published' ? 'Published' : 'Draft — images will not appear publicly until this record is published.'}</p>
        <p>Record IDs identify exhibitions, objects or events. Image IDs identify individual files and are separate numbers.</p>
        <MediaUploader key={`${ownerType}:${selected.id}`} ownerType={ownerType} ownerId={selected.id} onBusyChange={setBusy} />
      </section>}
    </div>
  );
}
