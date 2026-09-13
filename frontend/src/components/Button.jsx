import styles from './Button.module.css';

/**
 * The only button in the app. If you need a new look, add a variant here
 * rather than writing a one-off button in a page — that is how design
 * systems drift apart.
 *
 * variant: 'primary' | 'ghost' | 'danger'
 * size:    'md' | 'sm'
 */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  type = 'button',
  ...rest
}) {
  const classes = [
    styles.btn,
    styles[variant],
    size === 'sm' ? styles.sm : '',
    fullWidth ? styles.full : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  );
}
