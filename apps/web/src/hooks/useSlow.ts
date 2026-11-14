import { useEffect, useState } from "react";

/** True once `active` has stayed true for `ms` — used to explain a long wait
 * (e.g. the server waking up) instead of leaving a bare spinner. */
export function useSlow(active: boolean, ms: number): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(active), active ? ms : 0);
    return () => clearTimeout(timer);
  }, [active, ms]);
  return slow;
}
