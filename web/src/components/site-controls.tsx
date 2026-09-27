"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy, Moon, Sun, Terminal } from "lucide-react";
import type { Locale } from "@/lib/i18n";

export function ThemeToggle({ locale }: { locale: Locale }) {
  function toggle() {
    const dark = document.documentElement.classList.toggle("dark");
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch { /* Optional preference. */ }
  }
  return <button type="button" className="icon-button theme-toggle" onClick={toggle}
    aria-label={locale === "it" ? "Cambia tema chiaro o scuro" : "Switch light or dark theme"}>
    <Sun className="sun-icon" size={18} aria-hidden="true" />
    <Moon className="moon-icon" size={18} aria-hidden="true" />
  </button>;
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

export function InstallCommands({ locale, copyLabel, copiedLabel }: { locale: Locale; copyLabel: string; copiedLabel: string }) {
  const [platform, setPlatform] = useState<"windows" | "unix">("windows");
  const python = platform === "windows" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";
  const bootstrapPython = platform === "windows" ? "python" : "python3";
  const command = `git clone https://github.com/Fanfulla/MCP_Trenitalia.git\ncd MCP_Trenitalia\n${bootstrapPython} -m venv .venv\n${python} -m pip install -r requirements.txt\n${python} update_data.py\n${python} server.py`;
  return <div className="install-terminal">
    <div className="terminal-bar"><span><Terminal size={15} aria-hidden="true" />{locale === "it" ? "Installazione locale" : "Local installation"}</span><CopyCommand key={platform} command={command} label={copyLabel} copiedLabel={copiedLabel} locale={locale} /></div>
    <div className="install-platform" role="group" aria-label={locale === "it" ? "Sistema operativo" : "Operating system"}>
      <button type="button" aria-pressed={platform === "windows"} onClick={() => setPlatform("windows")}>Windows</button>
      <button type="button" aria-pressed={platform === "unix"} onClick={() => setPlatform("unix")}>macOS / Linux</button>
    </div>
    <pre><code>{command.split("\n").map((line, index) => <span className="code-line" key={index}><span className="line-number" aria-hidden="true">{index + 1}</span>{line}{"\n"}</span>)}</code></pre>
  </div>;
}
