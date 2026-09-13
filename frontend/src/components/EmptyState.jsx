import styles from './EmptyState.module.css';

/**
 * Shown when a list has nothing in it, or a request failed.
 *
 * An empty screen is an invitation to act, so always give at least one way
 * forward. Never apologise, and never leave the person on a dead end.
 */
export default function EmptyState({ title, body, children }) {
  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>{title}</h3>
      {body && <p className={styles.body}>{body}</p>}
      {children && <div className={styles.actions}>{children}</div>}
    </div>
  );
}
