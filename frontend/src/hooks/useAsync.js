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
 *
 * `deps` must be primitives (ids, strings, numbers, booleans): they form the
 * request key. Loading is derived from that key rather than set inside an
 * effect, so the render that changes a dependency already reports
 * loading: true -- a page never sees the previous request's result labelled
 * as current. `data` keeps the previous result while the next one loads.
 * Only the latest request's result is kept; slower earlier responses are
 * dropped.
 */
export default function useAsync(asyncFn, deps = []) {
  const [nonce, setNonce] = useState(0);
  const key = `${JSON.stringify(deps)}#${nonce}`;
  const [result, setResult] = useState({ key: null, data: null, error: null });

  // Always call the newest closure without making it part of the request key.
  const fnRef = useRef(asyncFn);
  useEffect(() => {
    fnRef.current = asyncFn;
  });

  useEffect(() => {
    let live = true;
    Promise.resolve()
      .then(() => fnRef.current())
      .then(
        (data) => live && setResult({ key, data, error: null }),
        (error) => live && setResult((prev) => ({ key, data: prev.data, error }))
      );
    return () => {
      live = false;
    };
  }, [key]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const loading = result.key !== key;

  return {
    data: loading || !result.error ? result.data : null,
    loading,
    error: loading ? null : result.error,
    reload,
  };
}
