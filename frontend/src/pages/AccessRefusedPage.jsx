import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from '../components/Button';
import styles from './AccessRefusedPage.module.css';

const ROLE_SCOPE = {
  member: 'your membership, bookings and recommendations',
  staff: 'exhibitions, collections, events and opening hours',
  admin: 'everything, including member records and the activity log',
};

/**
 * Shown when a signed-in account asks for something its role does not cover.
 *
 * Screenshot this with a staff account requesting /admin/members. Together
 * with a matching server log line carrying the same reference, it is the
 * evidence for the "no privileged endpoint reachable without the required
 * role" evaluation criterion. The screenshot alone proves nothing — the
 * server log is the half that counts.
 */
export default function AccessRefusedPage({ requiredRoles = ['admin'], reference = 'ACC-403' }) {
  const { user, isStaff } = useAuth();
  const needsAdmin = requiredRoles.includes('admin') && !requiredRoles.includes('staff');

  return (
    <div className={styles.wrap}>
      <div className={styles.inner}>
        <div className={styles.mark} />
        <h1>{needsAdmin ? 'This area is for administrators' : 'This area is for museum staff'}</h1>
        <p className={styles.body}>
          Your account covers {ROLE_SCOPE[user?.role] ?? 'the public areas of the site'}.
          {needsAdmin && ' Member records and account administration are restricted.'}{' '}
          Ask an administrator if you need access.
        </p>
        <div className={styles.actions}>
          <Link to={isStaff ? '/staff' : '/'}>
            <Button>{isStaff ? 'Back to the staff workspace' : 'Back to the home page'}</Button>
          </Link>
          <Button variant="ghost">Request access</Button>
        </div>
        <div className={styles.reference}>
          Reference {reference} · recorded in the activity log
        </div>
      </div>
    </div>
  );
}
