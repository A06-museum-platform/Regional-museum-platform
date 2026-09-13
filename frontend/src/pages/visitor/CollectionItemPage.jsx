import { Link, useNavigate, useParams } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { getCollectionItem, getRelatedItems } from '../../api/collections';
import { galleryLabel, categoryLabel } from '../../api/constants';
import CollectionCard from '../../components/CollectionCard';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './CollectionItemPage.module.css';

const THUMBS = {
  mineral:    'linear-gradient(135deg, #3B5417, #4C6B1F)',
  instrument: 'linear-gradient(135deg, #8A6A1A, #C08A1E)',
  document:   'linear-gradient(135deg, #4A4636, #6E6A50)',
  photograph: 'linear-gradient(135deg, #2A3524, #47543C)',
  machinery:  'linear-gradient(135deg, #5A5140, #8A7C60)',
};

/**
 * A single object, distinct from an exhibition page: an exhibition groups
 * objects, an object belongs to at most one exhibition. The client asked for
 * both, so do not merge them.
 */
export default function CollectionItemPage() {
  const { slug } = useParams();
  const navigate = useNavigate();

  const { data: item, loading, error } = useAsync(() => getCollectionItem(slug), [slug]);
  const { data: related } = useAsync(
    () => (item ? getRelatedItems(item) : Promise.resolve([])),
    [item?.id]
  );

  if (loading) {
    return (
      <div>
        <Skeleton height={12} width="30%" />
        <div style={{ height: 'var(--s-4)' }} />
        <div className={styles.layout}>
          <Skeleton height={340} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            <Skeleton height={18} width="40%" />
            <Skeleton height={30} width="80%" />
            <Skeleton height={60} />
            <Skeleton height={180} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    const notFound = error.status === 404;
    return (
      <EmptyState
        title={notFound ? 'We could not find that object' : 'We could not load that object'}
        body={
          notFound
            ? 'The link may be out of date, or the record may have been withdrawn from display.'
            : error.message
        }
      >
        <Button onClick={() => navigate('/collections')}>Back to collections</Button>
      </EmptyState>
    );
  }

  return (
    <div>
      <nav className={styles.crumbs} aria-label="Breadcrumb">
        <Link to="/collections">Collections</Link>
        {' / '}
        <Link to={`/collections?category=${item.category}`}>
          {categoryLabel(item.category)}
        </Link>
        {' / '}
        {item.title}
      </nav>

      <div className={styles.layout}>
        <div
          className={styles.image}
          style={{ background: THUMBS[item.category] || THUMBS.document }}
          role="img"
          aria-label={`Placeholder image for ${item.title}`}
        />

        <div>
          <div className={styles.pills}>
            <Pill>{categoryLabel(item.category)}</Pill>
            {item.is_family_friendly && <Pill tone="lime">Good for ages 10–14</Pill>}
          </div>

          <h1 className={styles.title}>{item.title}</h1>
          <p className={styles.description}>{item.description}</p>

          <table className={styles.facts}>
            <tbody>
              <tr>
                <th scope="row">Accession number</th>
                <td>{item.accession_number}</td>
              </tr>
              <tr>
                <th scope="row">On display at</th>
                <td>{galleryLabel(item.gallery)}</td>
              </tr>
              <tr>
                <th scope="row">Date</th>
                <td>{item.period_text}</td>
              </tr>
              <tr>
                <th scope="row">Materials</th>
                <td>{item.materials}</td>
              </tr>
              <tr>
                <th scope="row">Part of</th>
                <td>
                  {item.exhibition ? (
                    <Link to={`/exhibitions/${item.exhibition.slug}`}>
                      {item.exhibition.title}
                    </Link>
                  ) : (
                    <span style={{ color: 'var(--c-muted)' }}>Not currently in an exhibition</span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>

          <div className={styles.actions}>
            <Link to="/visit"><Button>Plan your visit</Button></Link>
            <Link to={`/collections?gallery=${item.gallery}`}>
              <Button variant="ghost">More from this gallery</Button>
            </Link>
          </div>
        </div>
      </div>

      {related && related.length > 0 && (
        <section className={styles.related}>
          <h2>Other {categoryLabel(item.category).toLowerCase()} records</h2>
          <div className={styles.relatedGrid}>
            {related.map((candidate) => (
              <CollectionCard key={candidate.id} item={candidate} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
