import { useState } from 'react';
import MediaUploader from '../../components/MediaUploader';
import Button from '../../components/Button';

export default function StaffMediaPage() {
  const [ownerType, setOwnerType] = useState('collection-item');
  const [recordId, setRecordId] = useState('6');
  const [selected, setSelected] = useState({ type: 'collection-item', id: 6 });
  return (
    <div>
      <h1>Media library</h1>
      <p>View and upload images for an existing museum record.</p>
      <form onSubmit={(event) => {
        event.preventDefault();
        setSelected({ type: ownerType, id: Number(recordId) });
      }} style={{ display: 'flex', gap: '1rem', alignItems: 'end', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div className="field">
          <label htmlFor="media-type">Record type</label>
          <select id="media-type" className="control" value={ownerType} onChange={(event) => setOwnerType(event.target.value)}>
            <option value="collection-item">Collection object</option>
            <option value="exhibition">Exhibition</option>
            <option value="event">Event</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="media-record">Record ID</label>
          <input id="media-record" className="control" type="number" min="1" step="1" required
            value={recordId} onChange={(event) => setRecordId(event.target.value)} />
        </div>
        <Button type="submit">Load images</Button>
      </form>
      <MediaUploader key={`${selected.type}:${selected.id}`} ownerType={selected.type} ownerId={selected.id} />
    </div>
  );
}
