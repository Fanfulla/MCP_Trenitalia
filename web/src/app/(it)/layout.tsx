import type { Metadata, Viewport } from "next";
import { SiteLayout, siteViewport } from "@/components/site-layout";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = { metadataBase: new URL(SITE_URL) };
export const viewport: Viewport = siteViewport;

export default function ItalianLayout({ children }: { children: React.ReactNode }) {
  return <SiteLayout locale="it">{children}</SiteLayout>;
}
