// TCGdex asset URLs come without an extension; webp is the lightest format it serves.
export function logoUrl(base: string | null): string | null {
  return base ? `${base}.webp` : null;
}
