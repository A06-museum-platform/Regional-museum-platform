import { useState } from 'react';
import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { listInterestTags, getMyInterests, saveMyInterests, getRecommendations, recommendationHref } from '../../api/recommendations';
import { galleryLabel } from '../../api/constants';
import { formatDate } from '../../utils/date';
import InterestPicker from './InterestPicker';
import Skeleton from '../Skeleton';
import Button from '../Button';
import Pill from '../Pill';
import styles from './Member.module.css';

const TYPE_LABEL = { exhibition: 'Exhibition', event: 'Workshop', collection_item: 'Object' };

/**
 * "Recommended for you" (client requirement 3(iv)). Members pick interests
 * and get exhibitions, workshops and objects ranked by how well they match.
 * A visitor account can choose interests too, but recommendations are a
 * member benefit, so it sees an invitation to join instead of the list.
 */
export default function RecommendationsPanel({ isMember }) {
  const tags = useAsync(() => listInterestTags(), []);
  const interests = useAsync(() => getMyInterests(), []);
  const recs = useAsync(
    () => (isMember ? getRecommendations({ size: 6 }) : Promise.resolve(null)),
    [isMember]
  );

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const chosen = interests.data?.map((t) => t.slug) ?? [];

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await saveMyInterests(draft);
      setEditing(false);
      interests.reload();
      recs.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="recs-heading">
      <div className={styles.panelHead}>
        <h2 id="recs-heading" className={styles.heading}>Recommended for you</h2>
        {!editing && tags.data && (
          <Button size="sm" variant="ghost" onClick={() => { setDraft(chosen); setEditing(true); }}>
            {chosen.length ? 'Change interests' : 'Choose interests'}
          </Button>
        )}
      </div>

      {editing ? (
        <div className={styles.editBox}>
          <InterestPicker tags={tags.data} selected={draft} onChange={setDraft}
            label="What would you like to see more of?" disabled={saving} />
          {error && <div className={styles.error} role="alert">{error}</div>}
          <div className={styles.actions}>
            <Button size="sm" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save interests'}</Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </div>
      ) : interests.data && chosen.length > 0 ? (
        <div className={styles.interestLine}>
          Your interests: {interests.data.map((t) => <Pill key={t.slug} tone="lime">{t.label}</Pill>)}
        </div>
      ) : null}

      {!isMember ? (
        <div className={styles.empty}>
          Recommendations are a member benefit. Choose your interests now and they will be ready
          the day your membership starts. <Link to="/membership">See memberships</Link>
        </div>
      ) : recs.loading ? (
        <div className={styles.recGrid}>{[1, 2, 3].map((n) => <Skeleton key={n} height={150} />)}</div>
      ) : recs.error ? (
        <div className={styles.empty}>{recs.error.message}</div>
      ) : recs.data.items.length === 0 ? (
        <div className={styles.empty}>
          Nothing matches those interests right now — new workshops are added every month.
          Try adding another interest.
        </div>
      ) : (
        <>
          {!recs.data.personalised && (
            <p className={styles.hint}>Choose a few interests to make these personal. Until then, here is what is popular.</p>
          )}
          <ul className={styles.recGrid}>
            {recs.data.items.map((rec) => (
              <li key={`${rec.type}-${rec.id}`}>
                <Link to={recommendationHref(rec)} className={styles.recCard}>
                  <div className={styles.recPills}>
                    <Pill>{TYPE_LABEL[rec.type]}</Pill>
                    {rec.gallery && <span className={styles.recGallery}>{galleryLabel(rec.gallery)}</span>}
                  </div>
                  <h3 className={styles.recTitle}>{rec.title}</h3>
                  {rec.starts_at && <div className={styles.recWhen}>{formatDate(rec.starts_at)}</div>}
                  <div className={styles.recReason}>{rec.reason}</div>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
