import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Runs an async function and tracks loading / data / error.
 *
 * Every page that fetches something needs the same three states, and every one
 * of them needs a skeleton for the loading case — the empty, error and loading
 * screens are where most failed usability-test tasks end up.
 *
 * Usage:
 *   const { data, loading, error, reload } = useAsync(
 *     () => searchCollections({ q }),
 *     [q]
 *   );
 */
export default function useAsync(asyncFn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const latest = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(asyncFn, deps);

  const execute = useCallback(() => {
    const requestId = ++latest.current;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    run()
      .then((data) => {
        // Ignore a response that has been superseded — otherwise typing fast
        // in the search box can render stale results.
        if (requestId !== latest.current) return;
        setState({ data, loading: false, error: null });
      })
      .catch((error) => {
        if (requestId !== latest.current) return;
        setState({ data: null, loading: false, error });
      });
  }, [run]);

  useEffect(() => {
    execute();
  }, [execute]);

  return { ...state, reload: execute };
}
