import { formatPrice } from '../../api/constants';
import Button from '../Button';
import styles from './Membership.module.css';

/** One tier on the plans page. The selected card gets the moss border. */
export default function MembershipPlanCard({ plan, selected, onSelect }) {
  const yearly = plan.duration_months === 12 ? '/year' : ` / ${plan.duration_months} months`;
  return (
    <div className={`${styles.plan} ${selected ? styles.planSelected : ''}`}>
      {plan.featured && <span className={styles.planBadge}>Most families choose this</span>}
      <h3 className={styles.planName}>{plan.display_name}</h3>
      <div className={styles.planPrice}>
        {formatPrice(plan.price_cents).replace('.00', '')}
        <span>{yearly}</span>
      </div>
      <ul className={styles.benefits}>
        {plan.benefits.map((benefit) => <li key={benefit}>{benefit}</li>)}
      </ul>
      <Button
        size="sm"
        fullWidth
        variant={selected ? 'primary' : 'ghost'}
        aria-pressed={selected}
        onClick={() => onSelect(plan)}
      >
        {selected ? 'Selected' : 'Select'}
      </Button>
    </div>
  );
}
