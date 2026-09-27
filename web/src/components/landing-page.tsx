import Link from "next/link";
import {
  ArrowDown, ArrowRight, ArrowUpRight, Check, Code2, Database, Github,
  Globe2, Layers3, Menu, Radio, ShieldCheck, Terminal, TrainFront,
} from "lucide-react";
import { translations, type Locale } from "@/lib/i18n";
import { AUTHOR_NAME, CONTENT_UPDATED, GITHUB_URL, X_URL, localePath } from "@/lib/site";
import { InstallCommands, ThemeToggle } from "./site-controls";

function XMark({ size = 18 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-6.8 7.8L23.2 22h-6.3L12 14.6 5.5 22H2.4l7.8-8.9L1.8 2h6.5l4.5 6.8L18.9 2Zm-1.1 18h1.7L7.3 3.9H5.5L17.8 20Z" /></svg>;
}

function External({ href, className, children, label }: { href: string; className?: string; children: React.ReactNode; label?: string }) {
  return <a href={href} target="_blank" rel="noopener noreferrer" className={className} aria-label={label}>{children}</a>;
}

function SectionHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description?: string }) {
  return <div className="section-heading"><p className="eyebrow">{eyebrow}</p><h2>{title}</h2>{description && <p className="section-description">{description}</p>}</div>;
}

export function LandingPage({ locale }: { locale: Locale }) {
  const t = translations[locale];
  const alternate = locale === "it" ? "en" : "it";
  const primaryTools = ["ciuff_cerca_viaggi", "ciuff_stato_treno", "ciuff_cerca_stazioni"].map(id => t.features.tools.find(tool => tool.id === id)!);
  const otherTools = t.features.tools.filter(tool => !primaryTools.includes(tool));
  return <>
    <a className="skip-link" href="#main-content">{t.accessibility.skip}</a>
    <header className="site-header">
      <div className="header-inner page-width">
        <Link href={localePath(locale)} className="brand" aria-label="MCP Trenitalia + Italo, Ciuff">
          <span className="brand-icon"><TrainFront size={22} strokeWidth={1.8} aria-hidden="true" /></span>
          <span>MCP Trenitalia <span className="brand-extension">+ Italo</span></span>
        </Link>
        <nav className="desktop-nav" aria-label={locale === "it" ? "Navigazione principale" : "Main navigation"}>
          <a href="#features">{t.nav.features}</a><a href="#demo">{t.nav.demo}</a><a href="#faq">{t.nav.faq}</a>
        </nav>
        <div className="header-actions">
          <Link className="locale-link" href={localePath(alternate)} hrefLang={alternate} lang={alternate} aria-label={t.accessibility.switchLanguage}><Globe2 size={15} aria-hidden="true" /><span>{alternate.toUpperCase()}</span></Link>
          <ThemeToggle locale={locale} />
          <External href={GITHUB_URL} className="header-github" label={t.accessibility.openGithub}><Github size={17} aria-hidden="true" /><span>GitHub</span><ArrowUpRight size={14} aria-hidden="true" /></External>
          <details className="mobile-nav"><summary aria-label={t.accessibility.menu}><Menu size={22} aria-hidden="true" /></summary><nav aria-label={t.accessibility.menu}><a href="#features">{t.nav.features}</a><a href="#demo">{t.nav.demo}</a><a href="#how-it-works">{t.nav.howItWorks}</a><a href="#faq">{t.nav.faq}</a><a href="#install">{t.nav.getStarted}</a><External href={X_URL}>X · @Fanfulladev</External></nav></details>
        </div>
      </div>
    </header>
    <main id="main-content">
      <section className="hero page-width" aria-labelledby="hero-title">
        <div className="hero-copy"><p className="release-badge"><span aria-hidden="true" />{t.hero.badge}</p>
          <h1 id="hero-title">{t.hero.title}<br /><span>{t.hero.titleAccent}</span></h1>
          <p className="hero-description">{t.hero.subtitle}</p>
          <div className="button-row"><External href={GITHUB_URL} className="button button-primary"><Github size={19} aria-hidden="true" />{t.hero.cta}<ArrowUpRight size={18} aria-hidden="true" /></External><External href={X_URL} className="button button-secondary"><XMark />{t.hero.ctaSecondary}</External></div>
          <div className="hero-facts"><span><Check size={14} aria-hidden="true" />Open source</span><span><Check size={14} aria-hidden="true" />{t.features.eyebrow}</span><span><Check size={14} aria-hidden="true" />{locale === "it" ? "Nessuna API a pagamento" : "No paid APIs"}</span></div>
          <a className="text-link hero-scroll" href="#install">{t.nav.getStarted}<ArrowDown size={15} aria-hidden="true" /></a>
        </div>
        <div className="terminal-preview" aria-label={t.preview.label}>
          <div className="terminal-bar"><div className="window-dots" aria-hidden="true"><i /><i /><i /></div><span>ciuff / MCP</span><span className="terminal-badge">{t.preview.label}</span></div>
          <div className="terminal-body"><div className="prompt-line"><span className="prompt-mark">›</span><p>{t.preview.question}</p></div>
            <div className="tool-call"><Terminal size={15} aria-hidden="true" /><code>ciuff_cerca_viaggi</code><span>JSON</span></div>
            <div className="route-heading"><div>Roma Termini<span>ROM</span></div><div className="rail-line" aria-hidden="true"><i /><span /><ArrowRight size={15} /></div><div>Milano Centrale<span>MIL</span></div></div>
            <div className="train-preview-row"><span className="operator-dot trenitalia" aria-hidden="true" /><div><strong>Trenitalia</strong><span>Frecciarossa 9516</span></div><div><strong>08:05 → 11:50</strong><span>{t.preview.scheduled}</span></div></div>
            <div className="train-preview-row"><span className="operator-dot italo" aria-hidden="true" /><div><strong>Italo</strong><span>9972</span></div><div><strong>08:05 → 11:15</strong><span>{t.preview.scheduled}</span></div></div>
            <div className="terminal-footer"><ShieldCheck size={15} aria-hidden="true" /><span>{t.preview.unknownDelay}</span></div>
          </div><p className="preview-caption">{t.preview.note}</p>
        </div>
      </section>
      <section className="integration-strip" aria-labelledby="integration-title"><div className="page-width integration-grid"><div><p className="eyebrow">{t.integration.eyebrow}</p><h2 id="integration-title">{t.integration.title}</h2></div><div><p>{t.integration.description}</p><div className="operator-labels">{t.integration.providers.map(provider => <span key={provider.name}><i className={`operator-dot ${provider.name.toLowerCase()}`} aria-hidden="true" />{provider.name}</span>)}</div></div></div></section>

      <section id="features" className="section page-width">
        <SectionHeading eyebrow={t.features.eyebrow} title={t.features.title} description={t.features.subtitle} />
        <div className="feature-grid">{primaryTools.map((tool, index) => {
          const Icon = [Layers3, Radio, TrainFront][index];
          return <article className="feature-card" key={tool.id}><div className="feature-top"><Icon size={25} strokeWidth={1.6} aria-hidden="true" /><span>0{index + 1}</span></div><h3>{tool.name}</h3><p>{tool.description}</p><code>{tool.id}</code><blockquote>{tool.example}</blockquote></article>;
        })}</div>
        <details className="all-tools"><summary>{locale === "it" ? "Esplora tutti gli 11 tool MCP" : "Explore all 11 MCP tools"}<span aria-hidden="true">+</span></summary><div className="tool-list">{otherTools.map(tool => <article key={tool.id}><div><h3>{tool.name}</h3><code>{tool.id}</code></div><p>{tool.description}</p></article>)}</div></details>
      </section>

      <section id="how-it-works" className="section architecture-section"><div className="page-width architecture-grid"><div className="architecture-intro"><SectionHeading eyebrow={t.howItWorks.eyebrow} title={t.howItWorks.title} description={t.howItWorks.subtitle} /><div className="architecture-note"><Database size={20} aria-hidden="true" /><p>{t.integration.note}</p></div></div><ol className="steps">{t.howItWorks.steps.map((step, index) => <li key={step.title}><span className="step-number">{String(index + 1).padStart(2, "0")}</span><div><h3>{step.title}</h3><p>{step.description}</p></div></li>)}</ol></div></section>

      <section id="demo" className="section page-width"><SectionHeading eyebrow={t.demo.eyebrow} title={t.demo.title} description={t.demo.subtitle} /><div className="demo-grid">{t.demo.videos.map((video, index) => <figure className={index === 2 ? "demo-video mobile-demo" : "demo-video"} key={video.src}><div className="video-frame"><video controls playsInline preload="none" width={index === 2 ? 720 : 1280} height={index === 2 ? 1560 : 720} poster={video.src.replace(".mp4", ".jpg")} aria-label={video.label}><source src={video.src} type="video/mp4" /><a href={video.src}>{video.label}</a></video></div><figcaption><span className="eyebrow">DEMO 0{index + 1}</span><h3>{video.label}</h3><p>{video.description}</p></figcaption></figure>)}</div></section>

      <section id="install" className="section install-section"><div className="page-width install-grid"><div><SectionHeading eyebrow={t.install.eyebrow} title={t.install.title} description={t.install.description} /><p className="install-requirements">{t.install.requirements}</p><External className="text-link" href={`${GITHUB_URL}#install`}>{t.install.docs}<ArrowUpRight size={16} aria-hidden="true" /></External><div className="stack-tags">{t.stack.items.map(item => <span title={item.description} key={item.name}>{item.name}</span>)}</div></div><InstallCommands locale={locale} copyLabel={t.install.copy} copiedLabel={t.install.copied} /></div></section>

      <section id="sources" className="section page-width sources-section"><div className="source-heading"><SectionHeading eyebrow={t.sources.eyebrow} title={t.sources.title} description={t.sources.description} /><p className="updated-label">{t.sources.updated} <time dateTime={CONTENT_UPDATED}>{new Intl.DateTimeFormat(locale, {dateStyle: "long", timeZone: "UTC"}).format(new Date(`${CONTENT_UPDATED}T00:00:00Z`))}</time></p></div><div className="source-grid">{t.sources.items.map(source => <article key={source.name}><External href={source.url}><h3>{source.name}</h3><ArrowUpRight size={16} aria-hidden="true" /></External><p>{source.description}</p></article>)}</div><div className="limitations"><ShieldCheck size={21} aria-hidden="true" /><ul>{t.sources.limitations.map(item => <li key={item}>{item}</li>)}</ul></div></section>

      <section id="faq" className="section page-width faq-section"><SectionHeading eyebrow={t.faq.eyebrow} title={t.faq.title} /><div className="faq-list">{t.faq.items.map(item => <details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div></section>

      <section className="closing-section page-width"><div className="closing-panel"><div className="closing-icon" aria-hidden="true"><Code2 size={28} /></div><h2>{t.cta.title}</h2><p>{t.cta.subtitle}</p><div className="button-row"><External href={GITHUB_URL} className="button button-primary"><Github size={19} aria-hidden="true" />{t.cta.github}<ArrowUpRight size={17} aria-hidden="true" /></External><External href={X_URL} className="button button-secondary"><XMark />{t.cta.x}</External></div></div></section>
    </main>
    <footer className="site-footer page-width"><div className="footer-top"><div><Link className="brand footer-brand" href={localePath(locale)}><TrainFront size={23} aria-hidden="true" /><span>MCP Trenitalia + Italo</span></Link><p>{t.footer.description}</p></div><div className="footer-links"><External href={GITHUB_URL}>GitHub<ArrowUpRight size={13} aria-hidden="true" /></External><External href={X_URL}>@Fanfulladev<XMark size={13} /></External><External href={`${GITHUB_URL}/blob/main/LICENSE`}>{t.footer.license}</External></div></div><div className="footer-bottom"><p>{t.footer.independent}</p><p>{t.footer.by} <External href="https://github.com/Fanfulla">{AUTHOR_NAME}</External> · <span>ciuff.org</span></p></div></footer>
  </>;
}
