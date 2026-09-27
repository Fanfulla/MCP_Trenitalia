"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Check, Copy, Menu, Moon, Sun, Terminal } from "lucide-react";
import type { Locale } from "@/lib/i18n";
import { THEME_COLORS } from "@/lib/site";

type Platform = "windows" | "unix";

function syncThemeColor(dark: boolean) {
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach(meta => {
    meta.content = dark ? THEME_COLORS.dark : THEME_COLORS.light;
  });
}

export function ThemeToggle({ locale }: { locale: Locale }) {
  useEffect(() => syncThemeColor(document.documentElement.classList.contains("dark")), []);
  function toggle() {
    const dark = document.documentElement.classList.toggle("dark");
    syncThemeColor(dark);
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch { /* Optional preference. */ }
  }
  return <button type="button" className="icon-button theme-toggle" onClick={toggle}
    aria-label={locale === "it" ? "Cambia tema chiaro o scuro" : "Switch light or dark theme"}>
    <Sun className="sun-icon" size={18} aria-hidden="true" />
    <Moon className="moon-icon" size={18} aria-hidden="true" />
  </button>;
}

export function MobileNav({ label, children }: { label: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const details = ref.current;
    const summary = details?.querySelector("summary");
    if (!details || !summary) return;
    const close = () => { details.open = false; };
    const onPointerDown = (event: PointerEvent) => { if (!details.contains(event.target as Node)) close(); };
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") { close(); summary.focus(); } };
    const onClick = (event: MouseEvent) => { if ((event.target as Element).closest("a")) close(); };
    const onToggle = () => {
      if (details.open) {
        document.addEventListener("pointerdown", onPointerDown);
        document.addEventListener("keydown", onKeyDown);
      } else {
        document.removeEventListener("pointerdown", onPointerDown);
        document.removeEventListener("keydown", onKeyDown);
      }
    };
    details.addEventListener("toggle", onToggle);
    details.addEventListener("click", onClick);
    return () => {
      details.removeEventListener("toggle", onToggle);
      details.removeEventListener("click", onClick);
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);
  return <details ref={ref} className="mobile-nav">
    <summary aria-label={label}><Menu size={22} aria-hidden="true" /></summary>
    <nav aria-label={label}>{children}</nav>
  </details>;
}

export function CopyCommand({ command, label, copiedLabel, locale }: { command: string; label: string; copiedLabel: string; locale: Locale }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true); setFailed(false);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2500);
    } catch { setFailed(true); }
  }
  return <div className="copy-control">
    <button className="copy-button" type="button" onClick={copy} aria-label={copied ? copiedLabel : label}>
      {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
      <span>{copied ? copiedLabel : label}</span>
    </button>
    <span className="sr-only" role="status">{failed ? (locale === "it" ? "Seleziona e copia i comandi qui sotto." : "Select and copy the commands below.") : copied ? copiedLabel : ""}</span>
  </div>;
}

const subscribePlatform = () => () => {};

function detectPlatform(): Platform {
  const nav = navigator as Navigator & { userAgentData?: { platform?: string } };
  const platform = nav.userAgentData?.platform || nav.platform || "";
  return /mac|linux|x11|cros/i.test(platform) && !/android|iphone|ipad|ipod/i.test(nav.userAgent) ? "unix" : "windows";
}

export function InstallCommands({ locale, copyLabel, copiedLabel }: { locale: Locale; copyLabel: string; copiedLabel: string }) {
  const detected = useSyncExternalStore(subscribePlatform, detectPlatform, (): Platform => "windows");
  const [choice, setChoice] = useState<Platform | null>(null);
  const platform = choice ?? detected;
  const python = platform === "windows" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";
  const bootstrapPython = platform === "windows" ? "python" : "python3";
  const command = `git clone https://github.com/Fanfulla/MCP_Trenitalia.git\ncd MCP_Trenitalia\n${bootstrapPython} -m venv .venv\n${python} -m pip install -r requirements.txt\n${python} update_data.py\n${python} server.py`;
  return <div className="install-terminal">
    <div className="terminal-bar"><span><Terminal size={15} aria-hidden="true" />{locale === "it" ? "Installazione locale" : "Local installation"}</span><CopyCommand key={platform} command={command} label={copyLabel} copiedLabel={copiedLabel} locale={locale} /></div>
    <div className="install-platform" role="group" aria-label={locale === "it" ? "Sistema operativo" : "Operating system"}>
      <button type="button" aria-pressed={platform === "windows"} onClick={() => setChoice("windows")}>Windows</button>
      <button type="button" aria-pressed={platform === "unix"} onClick={() => setChoice("unix")}>macOS / Linux</button>
    </div>
    <pre translate="no"><code>{command.split("\n").map((line, index) => <span className="code-line" key={index}><span className="line-number" aria-hidden="true">{index + 1}</span>{line}{"\n"}</span>)}</code></pre>
  </div>;
}
