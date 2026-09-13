import { useEffect, useState } from 'react';

/**
 * Delays a value until it stops changing for `delay` ms.
 *
 * Without this, typing "telegraph" fires nine searches. Against mocks that is
 * merely wasteful; against Ray's API during the 500-concurrent-user load test
 * it is the difference between passing and not.
 */
export default function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
