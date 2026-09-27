import type { Metadata } from "next";
import { translations, type Locale } from "@/lib/i18n";
import { AUTHOR_NAME, CONTENT_UPDATED, GITHUB_URL, SITE_NAME, SITE_URL, X_URL, localePath } from "@/lib/site";

export const languageUrls = {
  it: `${SITE_URL}/`,
  en: `${SITE_URL}/en`,
  "x-default": `${SITE_URL}/`,
};

export function pageMetadata(locale: Locale): Metadata {
  const { title, description } = translations[locale].seo;
  const url = `${SITE_URL}${localePath(locale)}`;
  const index = process.env.VERCEL_ENV !== "preview";
  const image = { url: `${SITE_URL}/opengraph-image`, width: 1200, height: 630, alt: `${SITE_NAME}: Trenitalia + Italo` };

  return {
    metadataBase: new URL(SITE_URL),
    title,
    description,
    applicationName: SITE_NAME,
    authors: [{ name: AUTHOR_NAME, url: X_URL }],
    creator: AUTHOR_NAME,
    manifest: "/manifest.json",
    alternates: { canonical: url, languages: languageUrls },
    robots: {
      index,
      follow: true,
      googleBot: { index, follow: true, "max-image-preview": "large", "max-snippet": -1, "max-video-preview": -1 },
    },
    openGraph: {
      title, description, url, siteName: SITE_NAME, type: "website",
      locale: locale === "it" ? "it_IT" : "en_US",
      alternateLocale: locale === "it" ? "en_US" : "it_IT",
      images: [image],
    },
    twitter: { card: "summary_large_image", creator: "@Fanfulladev", title, description, images: [image] },
    category: "technology",
  };
}

export function structuredData(locale: Locale): string {
  const content = translations[locale];
  const url = `${SITE_URL}${localePath(locale)}`;
  const authorId = `${SITE_URL}/#author`;
  const softwareId = `${SITE_URL}/#software`;
  const websiteId = `${SITE_URL}/#website`;

  return JSON.stringify({
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Person", "@id": authorId, name: AUTHOR_NAME,
        sameAs: ["https://github.com/Fanfulla", X_URL],
      },
      {
        "@type": "SoftwareSourceCode", "@id": softwareId, name: SITE_NAME,
        description: content.seo.description, url: `${SITE_URL}/`,
        codeRepository: GITHUB_URL, programmingLanguage: "Python", runtimePlatform: "Python 3.12+",
        license: `${GITHUB_URL}/blob/main/LICENSE`, isAccessibleForFree: true,
        author: { "@id": authorId },
      },
      {
        "@type": "WebSite", "@id": websiteId, name: SITE_NAME, url: `${SITE_URL}/`,
        inLanguage: ["it", "en"], about: { "@id": softwareId }, publisher: { "@id": authorId },
      },
      {
        "@type": ["WebPage", "FAQPage"], "@id": `${url}#webpage`, url,
        name: content.seo.title, description: content.seo.description, inLanguage: locale,
        dateModified: CONTENT_UPDATED, isPartOf: { "@id": websiteId },
        about: { "@id": softwareId }, author: { "@id": authorId },
        mainEntity: content.faq.items.map(({ question, answer }) => ({
          "@type": "Question", name: question,
          acceptedAnswer: { "@type": "Answer", text: answer },
        })),
      },
    ],
  }).replace(/</g, "\\u003c");
}
