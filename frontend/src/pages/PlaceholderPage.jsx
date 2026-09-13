/**
 * Temporary stand-in so every route resolves while the real pages are built.
 * Delete this file once the last placeholder route is replaced — if it is
 * still here in Week 8, something was missed.
 */
export default function PlaceholderPage({ title, note }) {
  return (
    <div>
      <h1>{title}</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        {note || 'This page has not been built yet.'}
      </p>
    </div>
  );
}
