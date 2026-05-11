/** Build a URL for files in `client/public/` (works with Vite `base` / GitHub Pages project sites). */
export function publicUrl(path: string): string {
  const base = import.meta.env.BASE_URL;
  const normalized = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${normalized}`;
}
