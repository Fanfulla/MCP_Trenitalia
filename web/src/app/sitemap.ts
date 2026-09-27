import type { MetadataRoute } from "next";
import { CONTENT_UPDATED } from "@/lib/site";
import { languageUrls } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  return [languageUrls.it, languageUrls.en].map((url) => ({
    url,
    lastModified: CONTENT_UPDATED,
    alternates: { languages: languageUrls },
  }));
}
