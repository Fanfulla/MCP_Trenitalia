# Ciuff website

The existing [ciuff.org](https://ciuff.org/) project website for the free, self-hosted MCP server covering Trenitalia and Italo. Italian is served at `/`; English at `/en`. Both are static, server-rendered pages with crawlable language links. The site has no paid services, trackers or client-side API calls to train providers.

## Local checks

```sh
npm ci
npm run lint
npm run build
npm run start
```

Against the running production build, in a separate terminal:

```sh
node scripts/check-seo.mjs http://localhost:3000
```

The Node-only check fetches both pages and verifies initial HTML language and content, localized titles/descriptions, self canonicals, reciprocal `it`/`en`/`x-default` alternates, author links, JSON-LD, visible FAQ agreement, sitemap dates, robots, the actual 1200 x 630 PNG and true 404 responses. Use `--preview` only when testing a build created with `VERCEL_ENV=preview`; it additionally expects the preview noindex metadata and response header. Run browser checks separately for layout, interactions, accessibility and responsive behavior.

## Content and indexing

- `src/lib/i18n.ts` owns visible localized copy, search descriptions and FAQ answers. JSON-LD reads those same answers.
- `src/lib/site.ts` owns the production origin, author/project links and `CONTENT_UPDATED`. Update the date only when the page's substantive content changes; sitemap timestamps must not change on each request or unrelated deployment.
- Separate root layouts set the correct initial `<html lang>`. `global-not-found.tsx` uses Next's `experimental.globalNotFound` option because this app has multiple root layouts. Missing URLs return 404 rather than redirecting to a homepage.
- Production allows crawling. Only the explicit Vercel `preview` environment adds `noindex`; robots still permits crawling so bots can read that directive. For previews on other hosts, set the same build environment value or configure an equivalent host-level noindex header.
- Canonicals always use `https://ciuff.org`. OG and Twitter cards share an actual generated PNG at `/opengraph-image`. The original icon routes and public icon are retained.
- Structured data describes the source repository, its independent author, the website and the visible page/FAQ. It contains no reviews, ratings or claims of affiliation with Trenitalia or Italo. FAQ markup does not imply eligibility for a Google FAQ rich result.

Google's [AI search guidance](https://developers.google.com/search/docs/appearance/ai-features) applies ordinary search requirements to AI Overviews and AI Mode: crawlable pages, accessible text and structured data consistent with visible content. It does not require an `llms.txt` file or special AI schema, and inclusion or ranking is not guaranteed. The implementation follows Google's [localized page guidance](https://developers.google.com/search/docs/specialty/international/localized-versions) with reciprocal language URLs.

## After production deployment

The domain owner must verify the property in [Google Search Console](https://search.google.com/search-console/about), submit `https://ciuff.org/sitemap.xml` and inspect both language URLs. No verification token is invented or included in source. Check live canonical URLs, indexing eligibility, host-level crawler access, social card rendering and [PageSpeed Insights](https://pagespeed.web.dev/). These owner-side/live checks are separate from the local build and smoke check.

Use Search Console performance and coverage reports to assess discovery over time. This project does not include a paid SEO service or claim verified search rankings or AI citations.
