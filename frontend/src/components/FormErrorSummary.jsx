import styles from './FormErrorSummary.module.css';

/**
 * Tells the person what is still missing, in one place, next to the button
 * they just pressed.
 *
 * The pattern this replaces — a permanently disabled submit button with no
 * explanation — is a reliable way to lose a usability-test participant: they
 * can see the button, they cannot press it, and nothing on screen says why.
 * Keep the button live, validate on submit, and name the problems.
 */
export default function FormErrorSummary({ errors }) {
  const messages = Object.values(errors);
  if (messages.length === 0) return null;

  return (
    <div className={styles.summary} role="alert">
      <strong>
        {messages.length === 1
          ? 'One thing still needs attention'
          : `${messages.length} things still need attention`}
      </strong>
      <ul className={styles.list}>
        {messages.map((message) => (
          <li key={message}>{message}</li>
        ))}
      </ul>
    </div>
  );
}
