import assert from "node:assert/strict";

const base = new URL(process.argv.find((arg) => /^https?:\/\//.test(arg)) ?? "http://localhost:3000");
const preview = process.argv.includes("--preview");
const canonicalBase = "https://ciuff.org";
const expectedAlternates = { it: `${canonicalBase}/`, en: `${canonicalBase}/en`, "x-default": `${canonicalBase}/` };
const decode = (text) => text.replace(/&(?:amp|quot|apos|lt|gt|#39|#x[\da-f]+|#\d+);/gi, (entity) => {
  const named = { "&amp;": "&", "&quot;": '"', "&apos;": "'", "&lt;": "<", "&gt;": ">", "&#39;": "'" };
  if (named[entity]) return named[entity];
  return String.fromCodePoint(entity.toLowerCase().startsWith("&#x") ? parseInt(entity.slice(3, -1), 16) : parseInt(entity.slice(2, -1), 10));
});
const normalize = (text) => decode(text).replace(/\s+/g, " ").trim();
const attributes = (tag) => Object.fromEntries([...tag.matchAll(/([\w:-]+)\s*=\s*(["'])(.*?)\2/g)].map(([, name, , value]) => [name.toLowerCase(), decode(value)]));
const tags = (html, name) => [...html.matchAll(new RegExp(`<${name}\\b[^>]*>`, "gi"))].map(([tag]) => attributes(tag));
async function get(path, status = 200) {
  const response = await fetch(new URL(path, base), { redirect: "manual", signal: AbortSignal.timeout(20000) });
  assert.equal(response.status, status, `${path}: HTTP ${status}`);
  return response;
}

const titles = [];
const descriptions = [];
let imagePath;
for (const [locale, path] of [["it", "/"], ["en", "/en"]]) {
  const response = await get(path);
  const html = await response.text();
  assert.equal(tags(html, "html")[0]?.lang, locale, `${path}: server-rendered html lang`);
  const head = html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1];
  assert.ok(head, `${path}: HTML head`);
  const links = tags(head, "link");
  const canonicals = links.filter((link) => link.rel === "canonical");
  assert.equal(canonicals.length, 1, `${path}: one canonical`);
  assert.equal(new URL(canonicals[0].href).href, new URL(path, canonicalBase).href, `${path}: self canonical`);
  for (const [language, url] of Object.entries(expectedAlternates)) {
    const alternates = links.filter((link) => link.rel === "alternate" && link.hreflang === language);
    assert.equal(alternates.length, 1, `${path}: one ${language} alternate`);
    assert.equal(new URL(alternates[0].href).href, url, `${path}: ${language} alternate URL`);
  }
  const metadata = tags(head, "meta");
  const meta = (name) => metadata.find((tag) => tag.name === name || tag.property === name)?.content;
  const title = head.match(/<title>(.*?)<\/title>/i)?.[1];
  assert.ok(title?.includes("Trenitalia") && title.includes("Italo"), `${path}: operator names in title`);
  titles.push(title);
  assert.ok(meta("description")?.length > 50, `${path}: descriptive summary`);
  descriptions.push(meta("description"));
  assert.equal(meta("robots")?.includes("noindex"), preview, `${path}: indexing matches deployment environment`);
  assert.equal((response.headers.get("x-robots-tag") ?? "").includes("noindex"), preview, `${path}: indexing header matches deployment environment`);
  assert.equal(meta("twitter:creator"), "@Fanfulladev", `${path}: correct X author`);
  assert.equal(meta("twitter:card"), "summary_large_image", `${path}: large social card`);
  assert.equal(meta("og:image:width"), "1200", `${path}: social image width`);
  assert.equal(meta("og:image:height"), "630", `${path}: social image height`);
  assert.equal(meta("og:locale"), locale === "it" ? "it_IT" : "en_US", `${path}: Open Graph locale`);
  const imageUrl = new URL(meta("og:image"));
  assert.equal(imageUrl.origin, canonicalBase, `${path}: social image on canonical host`);
  imagePath = `${imageUrl.pathname}${imageUrl.search}`;
  assert.ok(meta("twitter:image"), `${path}: Twitter image`);

  const visibleHtml = html.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, "");
  const visibleText = normalize(visibleHtml.replace(/<[^>]*>/g, " "));
  assert.equal([...visibleHtml.matchAll(/<h1\b/gi)].length, 1, `${path}: one visible h1`);
  assert.ok(visibleText.includes("Trenitalia") && visibleText.includes("Italo"), `${path}: both operators in initial HTML`);
  assert.ok(tags(visibleHtml, "a").some((link) => link.href === (locale === "it" ? "/en" : "/")), `${path}: crawlable language switch`);
  assert.ok(tags(visibleHtml, "a").some((link) => link.href === "https://x.com/Fanfulladev"), `${path}: visible X link`);
  assert.ok(tags(visibleHtml, "a").some((link) => link.href === "https://github.com/Fanfulla/MCP_Trenitalia"), `${path}: visible repository link`);
  const jsonLd = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter(([, attrs]) => attributes(attrs).type === "application/ld+json")
    .map(([, , content]) => JSON.parse(content));
  assert.equal(jsonLd.length, 1, `${path}: one JSON-LD document`);
  const graph = jsonLd[0]["@graph"];
  const hasType = (node, type) => [node["@type"]].flat().includes(type);
  for (const type of ["Person", "SoftwareSourceCode", "WebSite", "WebPage", "FAQPage"]) {
    assert.ok(graph.some((node) => hasType(node, type)), `${path}: ${type} entity`);
  }
  const author = graph.find((node) => hasType(node, "Person"));
  assert.ok(author.sameAs.includes("https://github.com/Fanfulla") && author.sameAs.includes("https://x.com/Fanfulladev"), `${path}: author identities`);
  const faq = graph.find((node) => hasType(node, "FAQPage"));
  assert.equal(faq.inLanguage, locale, `${path}: FAQ language`);
  assert.ok(faq.mainEntity.length > 0, `${path}: FAQ content`);
  for (const question of faq.mainEntity) {
    assert.ok(visibleText.includes(normalize(question.name)), `${path}: visible FAQ question: ${question.name}`);
    assert.ok(visibleText.includes(normalize(question.acceptedAnswer.text)), `${path}: visible FAQ answer: ${question.name}`);
  }
  assert.ok(!JSON.stringify(graph).includes("aggregateRating"), `${path}: no fabricated ratings`);
  console.log(`PASS ${path}: language, canonical, hreflang, metadata, initial content and ${faq.mainEntity.length} matching FAQs`);
}
assert.notEqual(titles[0], titles[1], "Localized titles differ");
assert.notEqual(descriptions[0], descriptions[1], "Localized descriptions differ");

const sitemap = await (await get("/sitemap.xml")).text();
const locations = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(([, url]) => new URL(url).href);
assert.deepEqual(locations.sort(), [expectedAlternates.it, expectedAlternates.en].sort(), "Sitemap includes exactly both canonical pages");
assert.equal([...sitemap.matchAll(/<lastmod>2026-09-27(?:T[^<]*)?<\/lastmod>/g)].length, 2, "Sitemap uses actual content revision date");
for (const [language, url] of Object.entries(expectedAlternates)) {
  assert.equal(tags(sitemap, "xhtml:link").filter((link) => link.hreflang === language && new URL(link.href).href === url).length, 2, `Sitemap: reciprocal ${language} alternates`);
}
const robots = await (await get("/robots.txt")).text();
assert.match(robots, /User-Agent:\s*\*/i);
assert.match(robots, /Allow:\s*\//i);
assert.ok(!/Disallow:\s*\//i.test(robots), "No content crawler block");
assert.ok(robots.includes(`${canonicalBase}/sitemap.xml`), "Robots links sitemap");

const imageResponse = await get(imagePath);
assert.match(imageResponse.headers.get("content-type") ?? "", /image\/png/);
const png = Buffer.from(await imageResponse.arrayBuffer());
assert.equal(png.subarray(1, 4).toString(), "PNG", "Social image is PNG");
assert.equal(png.readUInt32BE(16), 1200, "Actual image width");
assert.equal(png.readUInt32BE(20), 630, "Actual image height");
for (const path of ["/seo-test-missing-page", "/en/seo-test-missing-page", "/fr"]) {
  const response = await get(path, 404);
  const html = await response.text();
  assert.ok(tags(html, "meta").some((tag) => tag.name === "robots" && tag.content?.includes("noindex")), `${path}: noindex 404`);
}
console.log("PASS sitemap, robots, actual 1200x630 PNG and three true 404 routes");
