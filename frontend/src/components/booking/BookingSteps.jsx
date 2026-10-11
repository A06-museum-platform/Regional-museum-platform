import styles from './Booking.module.css';

const STEPS = ['Choose your visit', 'Your details', 'Confirmation'];

/**
 * "1. Choose your visit / 2. Your details / 3. Confirmation".
 * Below the breakpoint it collapses to "Step 2 of 3" and a progress bar,
 * as in the responsive reference frame.
 */
export default function BookingSteps({ current }) {
  return (
    <>
      <ol className={styles.steps} aria-label="Booking progress">
        {STEPS.map((label, index) => {
          const number = index + 1;
          const isCurrent = number === current;
          return (
            <li
              key={label}
              className={`${styles.step} ${isCurrent ? styles.stepCurrent : ''}`}
              aria-current={isCurrent ? 'step' : undefined}
            >
              {number}. {label}
            </li>
          );
        })}
      </ol>
      <div className={styles.stepsMobile} aria-hidden="true">
        <div className={styles.stepsMobileLabel}>
          Step {current} of {STEPS.length} · {STEPS[current - 1]}
        </div>
        <div className={styles.progress}>
          <div className={styles.progressFill} style={{ width: `${(current / STEPS.length) * 100}%` }} />
        </div>
      </div>
    </>
  );
}
