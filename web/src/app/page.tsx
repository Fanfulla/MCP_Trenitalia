"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { type Locale, translations } from "@/lib/i18n";
import {
  Search,
  ArrowUpRight,
  ArrowDownLeft,
  MapPin,
  Route,
  Train,
  Github,
  Linkedin,
  ChevronRight,
  Globe,
  Terminal,
  Zap,
  Shield,
  Database,
  Cpu,
  ExternalLink,
  Menu,
  X,
  Sun,
  Moon,
  Copy,
  Check,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

/* ──────────────────────── Theme ──────────────────────── */

function useTheme() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("theme") as "dark" | "light" | null;
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
    const initial = saved || preferred;
    setTheme(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    localStorage.setItem("theme", next);
  };

  return { theme, toggle };
}

/* ──────────────────────── Animated Background ──────────────────────── */

function AnimatedOrb({
  delay = 0,
  duration = 20,
  size = 400,
  className = "",
}: {
  delay?: number;
  duration?: number;
  size?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={`absolute rounded-full blur-3xl pointer-events-none ${className}`}
      style={{ width: size, height: size }}
      animate={{
        x: [0, 80, -80, 0],
        y: [0, -60, 60, 0],
        scale: [1, 1.2, 0.9, 1],
      }}
      transition={{ duration, repeat: Infinity, delay, ease: "easeInOut" }}
    />
  );
}

function GridPattern() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-[0.04] dark:opacity-[0.06]">
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `linear-gradient(to right, rgba(139,92,246,0.5) 1px, transparent 1px),
                           linear-gradient(to bottom, rgba(139,92,246,0.5) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />
    </div>
  );
}

/* ──────────────────────── Typing Terminal ──────────────────────── */

function TerminalPreview({ locale }: { locale: Locale }) {
  const [currentLine, setCurrentLine] = useState(0);
  const hasAnimated = useRef(false);

  const lines =
    locale === "it"
      ? [
          { type: "user" as const, text: "Che treni passano da Tuscolana verso Aurelia stamattina?" },
          { type: "tool" as const, text: "trenitalia_orari_tra_stazioni" },
          { type: "result" as const, text: "FL3 12842  08:12 → 08:34  ✓ in orario" },
          { type: "result" as const, text: "FL3 12844  08:42 → 09:04  ⚠ +3 min" },
          { type: "result" as const, text: "FL3 12846  09:12 → 09:34  ✓ in orario" },
          { type: "info" as const, text: "3 treni trovati • dati live Viaggiatreno" },
        ]
      : [
          { type: "user" as const, text: "What trains from Tuscolana to Aurelia this morning?" },
          { type: "tool" as const, text: "trenitalia_orari_tra_stazioni" },
          { type: "result" as const, text: "FL3 12842  08:12 → 08:34  ✓ on time" },
          { type: "result" as const, text: "FL3 12844  08:42 → 09:04  ⚠ +3 min" },
          { type: "result" as const, text: "FL3 12846  09:12 → 09:34  ✓ on time" },
          { type: "info" as const, text: "3 trains found • live Viaggiatreno data" },
        ];

  useEffect(() => {
    if (hasAnimated.current) {
      setCurrentLine(lines.length);
      return;
    }
    if (currentLine < lines.length) {
      const delay = currentLine === 0 ? 800 : currentLine === 1 ? 400 : 300;
      const timer = setTimeout(() => setCurrentLine((c) => c + 1), delay);
      return () => clearTimeout(timer);
    } else {
      hasAnimated.current = true;
    }
  }, [currentLine, lines.length]);

  useEffect(() => {
    hasAnimated.current = false;
    setCurrentLine(0);
  }, [locale]);

  const lineColor = {
    user: "text-blue-500 dark:text-blue-400",
    tool: "text-green-600 dark:text-green-400",
    result: "text-foreground/80",
    info: "text-purple-600 dark:text-purple-400",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 40, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.9, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="relative w-full max-w-2xl mx-auto group/terminal"
    >
      {/* Outer glow — intensifies on hover */}
      <div className="absolute -inset-4 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-blue-500/10 dark:from-blue-600/15 dark:via-purple-600/15 dark:to-blue-600/15 rounded-3xl blur-2xl -z-10 transition-opacity duration-500 group-hover/terminal:opacity-100 opacity-70" />
      <div className="absolute -inset-8 bg-gradient-to-b from-blue-500/5 to-purple-500/5 dark:from-blue-500/8 dark:to-purple-500/8 rounded-[2rem] blur-3xl -z-20 opacity-0 group-hover/terminal:opacity-100 transition-opacity duration-700" />

      <div className="relative rounded-2xl overflow-hidden border border-border/80 dark:border-white/[0.1] bg-white/80 dark:bg-[#0c0c18]/80 backdrop-blur-2xl shadow-2xl shadow-black/10 dark:shadow-black/50 transition-all duration-500 group-hover/terminal:border-blue-500/20 dark:group-hover/terminal:border-blue-500/25 group-hover/terminal:shadow-blue-500/5 dark:group-hover/terminal:shadow-blue-500/10">
        {/* Header — macOS style */}
        <div className="flex items-center px-5 py-3.5 border-b border-border/50 dark:border-white/[0.06] bg-gradient-to-r from-muted/40 to-muted/20 dark:from-white/[0.03] dark:to-white/[0.01]">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57] shadow-[0_0_4px_rgba(255,95,87,0.4)]" />
            <div className="w-3 h-3 rounded-full bg-[#febc2e] shadow-[0_0_4px_rgba(254,188,46,0.4)]" />
            <div className="w-3 h-3 rounded-full bg-[#28c840] shadow-[0_0_4px_rgba(40,200,64,0.4)]" />
          </div>
          <div className="flex-1 flex items-center justify-center gap-2 text-xs text-muted-foreground/70">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-60"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>
            <span className="font-mono tracking-wider">Claude Desktop</span>
          </div>
          <div className="w-[62px]" /> {/* Spacer to center title */}
        </div>

        {/* Content */}
        <div className="p-5 sm:p-7 font-mono text-[13px] sm:text-sm min-h-[240px]">
          {/* User query */}
          {currentLine > 0 && (
            <motion.div
              key={`${locale}-user`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="mb-5"
            >
              <div className="flex gap-2 items-start">
                <span className="text-muted-foreground/40 select-none text-base leading-snug">›</span>
                <span className="text-blue-600 dark:text-blue-400 leading-snug">{lines[0].text}</span>
              </div>
            </motion.div>
          )}

          {/* Tool call badge */}
          {currentLine > 1 && (
            <motion.div
              key={`${locale}-tool`}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="mb-4 ml-4"
            >
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-green-500/10 dark:bg-green-500/15 border border-green-500/20 px-3 py-1.5 text-xs text-green-600 dark:text-green-400 font-medium">
                <Zap className="w-3 h-3" />
                {lines[1].text}
              </span>
            </motion.div>
          )}

          {/* Results */}
          {currentLine > 2 && (
            <motion.div
              key={`${locale}-results`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="ml-4 space-y-1.5 mb-4"
            >
              {lines.slice(2, 5).map((line, i) => (
                <motion.div
                  key={`${locale}-r-${i}`}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2, delay: i * 0.1 }}
                  className="flex items-center gap-3 text-foreground/80 py-0.5"
                >
                  <span className="text-muted-foreground/30 text-[10px] font-mono tabular-nums w-3 text-right">{i + 1}</span>
                  <span>{line.text}</span>
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* Info line */}
          {currentLine > 5 && (
            <motion.div
              key={`${locale}-info`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="ml-4 pt-3 border-t border-border/50 dark:border-white/[0.05]"
            >
              <span className="text-purple-600 dark:text-purple-400 text-xs">{lines[5].text}</span>
            </motion.div>
          )}

          {/* Typing cursor */}
          {currentLine < lines.length && currentLine <= 1 && (
            <div className="ml-4 mt-2">
              <motion.span
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 0.7, repeat: Infinity }}
                className="inline-block w-[7px] h-[15px] bg-blue-500 dark:bg-blue-400 rounded-[1px]"
              />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

/* ──────────────────────── Feature Card ──────────────────────── */

function FeatureCard({
  icon: Icon,
  name,
  id,
  description,
  example,
  index,
  span,
}: {
  icon: React.ComponentType<{ className?: string }>;
  name: string;
  id: string;
  description: string;
  example: string;
  index: number;
  span?: string;
}) {
  const [copied, setCopied] = useState(false);
  const copyExample = useCallback(() => {
    navigator.clipboard.writeText(example.replace(/^"|"$/g, ""));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [example]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: [0.25, 0.4, 0.25, 1] }}
      className={`group relative ${span || ""}`}
    >
      <div className="relative h-full overflow-hidden rounded-2xl border border-border bg-white/50 dark:bg-slate-950/40 backdrop-blur-xl hover:border-purple-500/25 dark:hover:border-blue-500/30 transition-all duration-500 shadow-sm hover:shadow-md dark:shadow-none">
        {/* Hover gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/[0.03] via-transparent to-purple-500/[0.03] dark:from-blue-500/[0.04] dark:to-purple-500/[0.04] opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        {/* Hover glow */}
        <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-purple-500/10 dark:bg-blue-500/20 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-all duration-500" />

        <div className="relative p-6 sm:p-7 h-full flex flex-col">
          <div className="mb-5">
            <div className="inline-flex p-3 rounded-2xl bg-blue-500/10 text-blue-600 dark:text-blue-400 group-hover:bg-blue-500/15 dark:group-hover:bg-blue-500/20 group-hover:text-blue-500 dark:group-hover:text-blue-300 transition-all duration-300 group-hover:scale-110">
              <Icon className="w-6 h-6" />
            </div>
          </div>

          <h3 className="text-xl font-bold text-foreground mb-1 group-hover:text-blue-700 dark:group-hover:text-blue-100 transition-colors">
            {name}
          </h3>
          <code className="text-[10px] text-muted-foreground/60 font-mono mb-3 block">
            {id}
          </code>

          <p className="text-sm text-muted-foreground leading-relaxed mb-5 flex-1">
            {description}
          </p>

          {/* Code example — click to copy */}
          <button
            onClick={copyExample}
            className="relative rounded-xl bg-muted/50 dark:bg-slate-950/70 border border-border group-hover:border-purple-500/15 dark:group-hover:border-blue-500/20 transition-colors text-left w-full cursor-pointer hover:bg-muted/70 dark:hover:bg-slate-950/90 overflow-hidden"
          >
            <div className="p-3.5 pb-2">
              <p className="text-xs text-blue-600/80 dark:text-blue-300/80 font-mono break-words whitespace-normal leading-relaxed">
                {example}
              </p>
            </div>
            <div className="flex items-center justify-end gap-1.5 px-3.5 pb-2.5 pt-0.5">
              {copied ? (
                <span className="flex items-center gap-1 text-[10px] text-green-500 font-medium">
                  <Check className="w-3 h-3" /> copied
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[10px] text-muted-foreground/40 group-hover:text-muted-foreground/70 transition-colors">
                  <Copy className="w-3 h-3" /> copy
                </span>
              )}
            </div>
          </button>
        </div>
      </div>
    </motion.div>
  );
}

/* ──────────────────────── Install Terminal (char-by-char typing) ── */

const INSTALL_LINES = [
  "git clone https://github.com/Fanfulla/MCP_Trenitalia.git",
  "cd MCP_Trenitalia",
  "uv venv && uv pip install -r requirements.txt",
  "python server.py",
];

function InstallTerminal({ locale }: { locale: Locale }) {
  const [charIndex, setCharIndex] = useState(0);
  const [started, setStarted] = useState(false);
  const [done, setDone] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Total chars across all lines (including \n separators)
  const fullText = INSTALL_LINES.join("\n");
  const totalChars = fullText.length;

  // Start typing when visible
  useEffect(() => {
    if (!ref.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStarted(true); },
      { threshold: 0.4 }
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  // Type character by character with variable speed
  useEffect(() => {
    if (!started || charIndex >= totalChars) {
      if (started && charIndex >= totalChars) setDone(true);
      return;
    }
    const currentChar = fullText[charIndex];
    // Newline = pause between commands (like pressing Enter)
    // Space = slightly faster
    // Otherwise normal typing speed with slight randomness
    let speed: number;
    if (currentChar === "\n") {
      speed = 250 + Math.random() * 150; // pause between lines
    } else if (currentChar === " ") {
      speed = 15 + Math.random() * 10;
    } else {
      speed = 20 + Math.random() * 25; // fast realistic typing
    }
    const timer = setTimeout(() => setCharIndex((c) => c + 1), speed);
    return () => clearTimeout(timer);
  }, [started, charIndex, totalChars, fullText]);

  // Split typed text back into lines
  const typedText = fullText.slice(0, charIndex);
  const typedLines = typedText.split("\n");
  const isTypingDone = done;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className="relative"
    >
      <div className="absolute -inset-2 bg-gradient-to-r from-blue-500/8 via-purple-500/8 to-blue-500/8 dark:from-blue-600/10 dark:via-purple-600/10 dark:to-blue-600/10 rounded-2xl blur-xl -z-10" />
      <div className="rounded-2xl overflow-hidden border border-border bg-white/70 dark:bg-slate-950/60 backdrop-blur-xl shadow-lg dark:shadow-none">
        <div className="flex items-center gap-2 px-5 py-3 border-b border-border bg-muted/30 dark:bg-white/[0.02]">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground font-mono">
            {locale === "it" ? "Installazione in locale" : "Local Installation"}
          </span>
        </div>
        <div className="p-5 sm:p-6 font-mono text-[13px] sm:text-sm space-y-1.5 min-h-[160px]">
          {typedLines.map((line, i) => {
            const isCurrentLine = i === typedLines.length - 1 && !isTypingDone;
            return (
              <div key={i} className="flex">
                <span className="text-green-600 dark:text-green-400 select-none shrink-0">$&nbsp; </span>
                <span>
                  <span className="text-foreground">{line}</span>
                  {isCurrentLine && (
                    <motion.span
                      animate={{ opacity: [1, 0.2, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity }}
                      className="inline-block w-[7px] h-[14px] bg-blue-500 dark:bg-blue-400 rounded-[1px] ml-[1px] align-middle relative top-[1px]"
                    />
                  )}
                </span>
              </div>
            );
          })}
          {isTypingDone && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="text-green-600 dark:text-green-400 text-xs mt-3 flex items-center gap-1"
            >
              <span>✓ {locale === "it" ? "Server MCP avviato su stdio" : "MCP Server started on stdio"}</span>
              <motion.span
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
                className="inline-block w-[7px] h-[14px] bg-blue-500 dark:bg-blue-400 rounded-[1px] ml-[1px] align-middle"
              />
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

/* ──────────────────────── Main Page ──────────────────────── */

export default function Home() {
  const [locale, setLocale] = useState<Locale>("it");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { theme, toggle: toggleTheme } = useTheme();
  const t = translations[locale];

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const toolIcons = [Search, ArrowUpRight, ArrowDownLeft, MapPin, Route];
  const stepIcons = [Database, Shield, Zap, Cpu];

  return (
    <main className="relative min-h-screen transition-colors duration-300" role="main">
      {/* ── Background ── */}
      <div className="fixed inset-0 -z-10 bg-gradient-to-br from-slate-50 via-blue-50/30 to-purple-50/20 dark:from-slate-950 dark:via-[#0a0a1a] dark:to-slate-950 transition-colors duration-300">
        <GridPattern />
        <AnimatedOrb delay={0} duration={22} size={500} className="top-[10%] left-[15%] bg-blue-400/10 dark:bg-blue-500/15" />
        <AnimatedOrb delay={4} duration={28} size={600} className="top-[30%] right-[10%] bg-purple-400/8 dark:bg-purple-500/12" />
        <AnimatedOrb delay={8} duration={24} size={450} className="bottom-[20%] left-[30%] bg-blue-400/6 dark:bg-blue-500/10" />
      </div>

      {/* ── Floating Navbar ── */}
      <header className="sticky top-4 z-50 mx-auto w-full max-w-4xl px-4 md:px-6">
        <nav aria-label="Main navigation" className="rounded-2xl border border-border/60 dark:border-white/[0.08] shadow-lg shadow-black/5 dark:shadow-black/20 bg-white/80 dark:bg-slate-950/70 supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-slate-950/50 backdrop-blur-xl transition-colors duration-300">
          <div className="flex items-center justify-between px-4 py-2 md:px-5">
            {/* Logo */}
            <a href="#" className="flex items-center gap-2 group rounded-lg px-2 py-1.5 hover:bg-muted/50 dark:hover:bg-white/[0.05] transition-colors">
              <div className="h-8 w-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                <Train className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              </div>
              <span className="font-bold tracking-tight text-foreground hidden sm:block">
                MCP Trenitalia
              </span>
            </a>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-1">
              <a href="#features" className="text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 dark:hover:bg-white/[0.05] rounded-lg px-3 py-1.5 transition-all">
                {t.nav.features}
              </a>
              <a href="#how-it-works" className="text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 dark:hover:bg-white/[0.05] rounded-lg px-3 py-1.5 transition-all">
                {t.nav.howItWorks}
              </a>

              <div className="w-px h-5 bg-border/60 dark:bg-white/[0.08] mx-1.5" />

              <button
                onClick={() => setLocale(locale === "it" ? "en" : "it")}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 dark:hover:bg-white/[0.05] rounded-lg px-2.5 py-1.5 transition-all cursor-pointer"
              >
                <Globe className="h-3.5 w-3.5" />
                {locale === "it" ? "IT" : "EN"}
              </button>
              <button
                onClick={toggleTheme}
                className="flex items-center justify-center h-8 w-8 rounded-lg hover:bg-muted/50 dark:hover:bg-white/[0.05] text-muted-foreground hover:text-foreground transition-all cursor-pointer"
                aria-label="Toggle theme"
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>

              <div className="w-px h-5 bg-border/60 dark:bg-white/[0.08] mx-1.5" />

              <a
                href="https://github.com/Fanfulla/MCP_Trenitalia"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-foreground text-background px-4 py-1.5 text-sm font-semibold hover:opacity-90 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <Github className="h-3.5 w-3.5" />
                {t.nav.getStarted}
              </a>
            </div>

            {/* Mobile controls */}
            <div className="flex md:hidden items-center gap-1">
              <button
                onClick={() => setLocale(locale === "it" ? "en" : "it")}
                className="text-sm text-muted-foreground hover:text-foreground rounded-lg px-2 py-1.5 transition-colors cursor-pointer flex items-center gap-1"
              >
                <Globe className="h-3.5 w-3.5" />
                {locale === "it" ? "IT" : "EN"}
              </button>
              <button
                onClick={toggleTheme}
                className="flex items-center justify-center h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground transition-all cursor-pointer"
                aria-label="Toggle theme"
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="flex items-center justify-center h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground cursor-pointer"
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>

          {/* Mobile dropdown */}
          <AnimatePresence>
            {mobileMenuOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="md:hidden overflow-hidden border-t border-border/40 dark:border-white/[0.06]"
              >
                <div className="px-4 py-3 flex flex-col gap-1">
                  <a href="#features" onClick={() => setMobileMenuOpen(false)} className="text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 dark:hover:bg-white/[0.05] rounded-lg px-3 py-2 transition-all">
                    {t.nav.features}
                  </a>
                  <a href="#how-it-works" onClick={() => setMobileMenuOpen(false)} className="text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 dark:hover:bg-white/[0.05] rounded-lg px-3 py-2 transition-all">
                    {t.nav.howItWorks}
                  </a>
                  <a
                    href="https://github.com/Fanfulla/MCP_Trenitalia"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-lg bg-foreground text-background px-4 py-2 text-sm font-semibold w-fit mt-1"
                  >
                    <Github className="h-3.5 w-3.5" />
                    {t.nav.getStarted}
                  </a>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </nav>
      </header>

      {/* ── Hero ── */}
      <section id="hero" aria-label="MCP Trenitalia — Server MCP per treni italiani in tempo reale" className="relative pt-16 pb-24 md:pt-24 md:pb-36 px-6">
        <div className="mx-auto max-w-4xl text-center">
          <motion.div initial={{ opacity: 0, y: -15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <span className="inline-flex items-center gap-2.5 rounded-full border border-blue-500/25 bg-blue-500/8 dark:bg-blue-500/10 backdrop-blur-sm px-5 py-2 text-xs font-medium text-blue-600 dark:text-blue-300 tracking-wide uppercase">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 dark:bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500 dark:bg-green-400" />
              </span>
              {t.hero.badge}
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="mt-10 text-5xl sm:text-6xl md:text-8xl font-bold tracking-tight leading-[1.05]"
          >
            <span className="text-foreground">{t.hero.title}</span>
            <br />
            <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 dark:from-blue-400 dark:via-purple-400 dark:to-blue-400 bg-clip-text text-transparent bg-[length:200%_auto] animate-[gradient-shift_4s_ease-in-out_infinite]">
              {t.hero.titleAccent}
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mt-7 text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed"
          >
            {t.hero.subtitle}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
            className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <a
              href="https://github.com/Fanfulla/MCP_Trenitalia"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2.5 rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white px-7 py-3.5 text-sm font-semibold shadow-lg shadow-blue-500/20 dark:shadow-blue-500/25 transition-all hover:scale-[1.03] active:scale-[0.98] hover:shadow-blue-500/30 dark:hover:shadow-blue-500/40"
            >
              <Github className="h-4 w-4" />
              {t.hero.cta}
              <ChevronRight className="h-4 w-4" />
            </a>
            <a
              href="https://www.linkedin.com/in/-salvatore-arena/"
              target="_blank"
              rel="noopener noreferrer"
              className="group/li inline-flex items-center gap-2.5 rounded-2xl border border-border hover:border-blue-400/40 dark:hover:border-blue-500/40 bg-white/50 dark:bg-white/[0.03] backdrop-blur-sm px-7 py-3.5 text-sm font-medium text-muted-foreground hover:text-blue-600 dark:hover:text-blue-300 transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] hover:shadow-lg hover:shadow-blue-500/10 dark:hover:shadow-blue-500/15 hover:bg-blue-50/70 dark:hover:bg-blue-500/[0.08]"
            >
              <Linkedin className="h-4 w-4" />
              {t.hero.ctaSecondary}
            </a>
          </motion.div>

          {/* Terminal */}
          <div className="mt-16 md:mt-24">
            <TerminalPreview locale={locale} />
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" aria-label="5 MCP tools per i treni italiani" className="py-24 md:py-36 px-6">
        <div className="mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16 md:mb-20"
          >
            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-[0.25em]">
              {t.features.eyebrow}
            </span>
            <h2 className="mt-5 text-3xl sm:text-4xl md:text-6xl font-bold tracking-tight text-foreground">
              {t.features.title}
            </h2>
            <p className="mt-5 text-muted-foreground max-w-xl mx-auto text-base sm:text-lg">
              {t.features.subtitle}
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {t.features.tools.map((tool, i) => (
              <FeatureCard
                key={tool.id}
                icon={toolIcons[i]}
                name={tool.name}
                id={tool.id}
                description={tool.description}
                example={tool.example}
                index={i}
                span={i >= 3 ? "md:col-span-1 lg:col-span-1" : undefined}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" aria-label="Come funziona MCP Trenitalia" className="py-24 md:py-36 px-6">
        <div className="mx-auto max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16 md:mb-20"
          >
            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-[0.25em]">
              {t.howItWorks.eyebrow}
            </span>
            <h2 className="mt-5 text-3xl sm:text-4xl md:text-6xl font-bold tracking-tight text-foreground">
              {t.howItWorks.title}
            </h2>
            <p className="mt-5 text-muted-foreground max-w-xl mx-auto text-base sm:text-lg">
              {t.howItWorks.subtitle}
            </p>
          </motion.div>

          <div className="relative">
            <div className="absolute left-[28px] top-6 bottom-6 w-px bg-gradient-to-b from-blue-500/10 via-purple-500/5 to-transparent dark:from-blue-500/30 dark:via-purple-500/15 hidden md:block" />

            <div className="space-y-6">
              {t.howItWorks.steps.map((step, i) => {
                const StepIcon = stepIcons[i];
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -30 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, margin: "-60px" }}
                    transition={{ duration: 0.5, delay: i * 0.12, ease: [0.25, 0.4, 0.25, 1] }}
                    className="group flex gap-5 items-start"
                  >
                    <div className="shrink-0 relative z-10 h-14 w-14 rounded-2xl bg-card border border-border flex items-center justify-center group-hover:border-blue-500/30 group-hover:bg-blue-500/10 transition-all duration-300">
                      <StepIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="pt-2 pb-4">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-[11px] font-mono text-blue-500/40 dark:text-blue-400/50 tabular-nums">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <h3 className="text-lg font-bold tracking-tight text-foreground group-hover:text-blue-700 dark:group-hover:text-blue-100 transition-colors">
                          {step.title}
                        </h3>
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed max-w-lg">
                        {step.description}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── Tech Stack ── */}
      <section className="py-20 md:py-28 px-6">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-14">
            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-[0.25em]">
              {t.stack.eyebrow}
            </span>
            <h2 className="mt-4 text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-foreground">
              {t.stack.title}
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {t.stack.items.map((item, i) => (
              <motion.div
                key={item.name}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="group rounded-2xl border border-border bg-card/50 backdrop-blur-sm p-4 text-center hover:border-purple-500/20 dark:hover:border-blue-500/20 hover:bg-purple-500/[0.04] dark:hover:bg-blue-500/[0.04] hover:shadow-md dark:hover:shadow-none hover:-translate-y-0.5 transition-all duration-300"
              >
                <p className="text-sm font-semibold text-foreground">{item.name}</p>
                <p className="text-[11px] text-muted-foreground mt-1">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Install snippet ── */}
      <section className="py-16 md:py-24 px-6">
        <div className="mx-auto max-w-2xl">
          <InstallTerminal locale={locale} />
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="py-24 md:py-36 px-6">
        <div className="mx-auto max-w-3xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-foreground">
              {t.cta.title}
            </h2>
            <p className="mt-6 text-muted-foreground text-base sm:text-lg max-w-xl mx-auto leading-relaxed">
              {t.cta.subtitle}
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href="https://github.com/Fanfulla/MCP_Trenitalia"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2.5 rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white px-7 py-4 text-sm font-semibold shadow-lg shadow-blue-500/20 dark:shadow-blue-500/25 transition-all hover:scale-[1.03] active:scale-[0.98]"
              >
                <Github className="h-4 w-4" />
                {t.cta.github}
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
              <a
                href="https://www.linkedin.com/in/-salvatore-arena/"
                target="_blank"
                rel="noopener noreferrer"
                className="group/li inline-flex items-center gap-2.5 rounded-2xl border border-blue-500/20 hover:border-blue-400/40 dark:hover:border-blue-500/40 bg-blue-500/[0.05] px-7 py-4 text-sm font-semibold text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-200 transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] hover:shadow-lg hover:shadow-blue-500/15 dark:hover:shadow-blue-500/20 hover:bg-blue-500/[0.1] dark:hover:bg-blue-500/[0.12]"
              >
                <Linkedin className="h-4 w-4" />
                {t.cta.linkedin}
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border py-8 px-6" role="contentinfo">
        <div className="mx-auto max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex flex-col items-center sm:items-start gap-1">
            <div className="flex items-center gap-2.5">
              <Train className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">{t.footer.domain}</span>
              <span className="text-xs text-muted-foreground italic">{t.footer.domainNote}</span>
            </div>
            <span className="text-xs text-muted-foreground sm:pl-6.5">{t.footer.description}</span>
          </div>
          <nav aria-label="Footer links" className="flex items-center gap-4">
            <a
              href="https://github.com/Fanfulla/MCP_Trenitalia"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              aria-label="MCP Trenitalia GitHub repository"
            >
              GitHub
            </a>
            <a
              href="https://www.linkedin.com/in/-salvatore-arena/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Salvatore Arena LinkedIn"
            >
              LinkedIn
            </a>
          </nav>
          <p className="text-sm text-muted-foreground">
            {t.footer.made} ❤️ {t.footer.by}{" "}
            <a
              href="https://github.com/Fanfulla"
              target="_blank"
              rel="noopener noreferrer"
              className="text-foreground font-medium hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              Fanfulla
            </a>
          </p>
        </div>
      </footer>
    </main>
  );
}
