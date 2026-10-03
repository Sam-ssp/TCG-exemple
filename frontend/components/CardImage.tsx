"use client";

import { ImageOff } from "lucide-react";
import { useState } from "react";

export function CardImage({ base, alt, quality }: { base: string | null; alt: string; quality: "low" | "high" }) {
  const [failed, setFailed] = useState(false);
  if (!base || failed) {
    return (
      <div className={`card-placeholder ${quality}`} role="img" aria-label={alt}>
        <ImageOff />
        <span aria-hidden="true">{alt}</span>
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- static export, images stay on TCGdex's CDN
    <img className={`card-img ${quality}`} src={`${base}/${quality}.webp`} alt={alt} loading="lazy" onError={() => setFailed(true)} />
  );
}
