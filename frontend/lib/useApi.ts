"use client";

import { useEffect, useState } from "react";
import { api } from "./api";
import { REFRESH_EVENT } from "./chat";
import type { RefreshTarget } from "./types";

export function useApi<T>(url: string | null, refreshOn: RefreshTarget[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const targets = refreshOn.join(",");

  useEffect(() => {
    if (!targets) return;
    const onRefresh = (event: Event) => {
      if (targets.split(",").includes((event as CustomEvent<RefreshTarget>).detail)) setVersion((v) => v + 1);
    };
    window.addEventListener(REFRESH_EVENT, onRefresh);
    return () => window.removeEventListener(REFRESH_EVENT, onRefresh);
  }, [targets]);

  useEffect(() => {
    if (url === null) return;
    let active = true;
    api<T>(url).then(
      (result) => {
        if (!active) return;
        setData(result);
        setError(null);
      },
      (err: Error) => {
        if (active) setError(err.message);
      },
    );
    return () => {
      active = false;
    };
  }, [url, version]);

  return { data, error, reload: () => setVersion((v) => v + 1) };
}
