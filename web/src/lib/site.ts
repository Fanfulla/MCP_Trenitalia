import type { Locale } from "./i18n";

export const SITE_URL = "https://ciuff.org";
export const GITHUB_URL = "https://github.com/Fanfulla/MCP_Trenitalia";
export const X_URL = "https://x.com/Fanfulladev";
export const AUTHOR_NAME = "Salvatore Arena";
export const CONTENT_UPDATED = "2026-09-27";
export const SITE_NAME = "MCP Trenitalia + Italo";
export const locales = ["it", "en"] as const;

export function localePath(locale: Locale): string {
  return locale === "it" ? "/" : "/en";
}
