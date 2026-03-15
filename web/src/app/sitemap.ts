import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://ciuff.org",
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
      alternates: {
        languages: {
          it: "https://ciuff.org",
          en: "https://ciuff.org",
        },
      },
    },
  ];
}
