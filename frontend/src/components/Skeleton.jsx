import styles from './Skeleton.module.css';

/**
 * Grey block in the shape of the content that is coming.
 *
 * Use this rather than a spinner: a skeleton tells people what is about to
 * appear and where, which is one less thing for a usability-test participant
 * to be confused by.
 */
export default function Skeleton({ height = 14, width = '100%', radius }) {
  return (
    <div
      className={styles.block}
      style={{ height, width, borderRadius: radius }}
      aria-hidden="true"
    />
  );
}
