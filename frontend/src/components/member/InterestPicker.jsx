import styles from './Member.module.css';

/**
 * Toggle chips for the interest vocabulary. Used by members on their account
 * page and by staff to tag content, so both sides speak the same words.
 */
export default function InterestPicker({ tags, selected, onChange, label = 'Interests', disabled }) {
  const toggle = (slug) =>
    onChange(selected.includes(slug) ? selected.filter((s) => s !== slug) : [...selected, slug]);

  return (
    <fieldset className={styles.picker} disabled={disabled}>
      <legend className={styles.pickerLegend}>{label}</legend>
      <div className={styles.chips}>
        {tags.map((tag) => {
          const on = selected.includes(tag.slug);
          return (
            <button
              key={tag.slug}
              type="button"
              className={`${styles.chip} ${on ? styles.chipOn : ''}`}
              aria-pressed={on}
              title={tag.description || undefined}
              onClick={() => toggle(tag.slug)}
            >
              {on ? '✓ ' : ''}{tag.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
