import { useEffect, useRef, useCallback } from "react";

/**
 * A hook that calls a function at a regular interval.
 * Useful for polling APIs for updates.
 *
 * @param callback - The function to call on each interval
 * @param interval - The interval in milliseconds
 * @param enabled - Whether the polling is enabled (default: true)
 */
export function usePolling(
  callback: () => Promise<void> | void,
  interval: number,
  enabled = true
) {
  const savedCallback = useRef(callback);

  // Remember the latest callback
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up the interval
  useEffect(() => {
    if (!enabled) return;

    // Call immediately on mount
    savedCallback.current();

    // Then set up the interval
    const id = setInterval(() => {
      savedCallback.current();
    }, interval);

    return () => clearInterval(id);
  }, [interval, enabled]);
}

export default usePolling;
