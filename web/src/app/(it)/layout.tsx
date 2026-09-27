import type { Metadata, Viewport } from "next";
import { SiteLayout } from "@/components/site-layout";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = { metadataBase: new URL(SITE_URL) };
export const viewport: Viewport = { themeColor: "#080b14", colorScheme: "dark" };

export default function ItalianLayout({ children }: { children: React.ReactNode }) {
  return <SiteLayout locale="it">{children}</SiteLayout>;
}
