import { Link } from 'react-router-dom';
import Button from '../components/Button';

export default function NotFoundPage() {
  return (
    <div style={{ textAlign: 'center', padding: 'var(--s-7) 0' }}>
      <h1>We could not find that page</h1>
      <p style={{ margin: '0 auto var(--s-5)', color: 'var(--c-muted)' }}>
        The link may be out of date. You can start again from the home page, or
        search the collection.
      </p>
      <Link to="/">
        <Button>Back to the home page</Button>
      </Link>
    </div>
  );
}
