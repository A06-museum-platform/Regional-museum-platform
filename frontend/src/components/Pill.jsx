import styles from './Pill.module.css';

/**
 * Small status or category label.
 *
 * tone: 'lime' (positive / active) | 'ochre' (pending / prototype)
 *     | 'grey' (neutral) | 'danger' (revoked / failed)
 *
 * Pass onRemove to render it as a dismissible filter chip.
 */
export default function Pill({ children, tone = 'grey', onRemove, removeLabel }) {
  return (
    <span className={`${styles.pill} ${styles[tone]}`}>
      {children}
      {onRemove && (
        <button
          type="button"
          className={styles.remove}
          onClick={onRemove}
          aria-label={removeLabel || `Remove ${children}`}
        >
          &times;
        </button>
      )}
    </span>
  );
}
