import { useEffect, useRef } from 'react';
import styles from './Modal.module.css';

/**
 * Dialog used for editors and confirmations.
 *
 * Escape closes it, focus moves inside on open, and the backdrop click closes
 * it too. Keyboard operation is part of the accessibility evidence for the
 * Week 9 evaluation, so do not strip these out for being fiddly.
 */
export default function Modal({ title, onClose, children, footer, narrow = false }) {
  const panelRef = useRef(null);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';
    panelRef.current?.querySelector('input, select, textarea, button')?.focus();

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  return (
    <div
      className={styles.backdrop}
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <div
        ref={panelRef}
        className={`${styles.panel} ${narrow ? styles.narrow : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className={styles.head}>
          <h2>{title}</h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>
        <div className={styles.body}>{children}</div>
        {footer && <div className={styles.foot}>{footer}</div>}
      </div>
    </div>
  );
}
