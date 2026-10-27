// Development-only harness; not an entry point in the production build.
import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import MediaImage from '../../src/components/MediaImage.jsx';

export default function Harness() {
  const query = new URLSearchParams(window.location.search);
  const [src, setSrc] = useState(query.get('src'));
  const lazy = query.has('lazy');
  return <>
    <button onClick={() => setSrc(query.get('next'))}>Change source</button>
    {lazy && <div style={{ height: 20000 }} />}
    <MediaImage src={src} alt="Browser drill image" loading={lazy ? 'lazy' : 'eager'}
      hideOnError={query.has('hide')} width="32" height="32" />
  </>;
}

createRoot(document.getElementById('root')).render(<Harness />);
