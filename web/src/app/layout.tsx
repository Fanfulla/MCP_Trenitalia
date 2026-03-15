import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://ciuff.org"),
  title: {
    default: "MCP Trenitalia — Treni italiani in tempo reale per la tua AI",
    template: "%s | MCP Trenitalia",
  },
  description:
    "Server MCP open source per dati ferroviari italiani in tempo reale. Orari, ritardi, partenze, arrivi e tracciamento treni live via Viaggiatreno + NeTEx. Compatibile con Claude, ChatGPT e altri LLM.",
  keywords: [
    "MCP Trenitalia",
    "MCP server treni",
    "Model Context Protocol",
    "treni italiani tempo reale",
    "Italian trains real time",
    "Viaggiatreno API",
    "NeTEx Italia",
    "Claude MCP",
    "AI treni",
    "orari treni",
    "ritardi treni",
    "partenze arrivi treni",
    "tracciamento treni live",
    "Trenitalia API",
    "open source railway",
    "FastMCP",
    "LLM tools",
    "train tracking Italy",
    "MCP server open source",
    "dati ferroviari italiani",
  ],
  authors: [{ name: "Salvatore Arena", url: "https://ciuff.org" }],
  creator: "Salvatore Arena",
  publisher: "Fanfulla",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  alternates: {
    canonical: "https://ciuff.org",
    languages: {
      "it-IT": "https://ciuff.org",
      "en-US": "https://ciuff.org",
    },
  },
  openGraph: {
    title: "MCP Trenitalia — Real-time Italian Trains for Your AI",
    description:
      "Open source MCP Server for real-time Italian railway data. Schedules, delays, departures, arrivals and live train tracking via Viaggiatreno + NeTEx.",
    url: "https://ciuff.org",
    siteName: "MCP Trenitalia",
    locale: "it_IT",
    alternateLocale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "MCP Trenitalia — Treni italiani in tempo reale per la tua AI",
    description:
      "Server MCP open source: orari, ritardi, partenze, arrivi e tracciamento treni live. Compatibile con Claude e altri LLM.",
    creator: "@_SalvatoreArena",
  },
  category: "technology",
};

/* ── JSON-LD Structured Data ── */
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      name: "MCP Trenitalia",
      applicationCategory: "DeveloperApplication",
      operatingSystem: "Cross-platform",
      description:
        "Open source MCP Server for real-time Italian railway data. Provides train schedules, delays, departures, arrivals and live tracking via Viaggiatreno and NeTEx APIs.",
      url: "https://ciuff.org",
      downloadUrl: "https://github.com/Fanfulla/MCP_Trenitalia",
      softwareVersion: "1.0",
      author: {
        "@type": "Person",
        name: "Salvatore Arena",
        url: "https://www.linkedin.com/in/-salvatore-arena/",
        sameAs: [
          "https://github.com/Fanfulla",
          "https://www.linkedin.com/in/-salvatore-arena/",
        ],
      },
      license: "https://opensource.org/licenses/MIT",
      programmingLanguage: ["Python"],
      keywords:
        "MCP, Trenitalia, Model Context Protocol, Italian trains, real-time, Viaggiatreno, NeTEx, Claude, AI, LLM",
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "EUR",
      },
      isAccessibleForFree: true,
    },
    {
      "@type": "WebSite",
      name: "MCP Trenitalia",
      url: "https://ciuff.org",
      description:
        "Server MCP open source per dati ferroviari italiani in tempo reale",
      inLanguage: ["it", "en"],
    },
    {
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: "Cos'è MCP Trenitalia?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "MCP Trenitalia è un server MCP (Model Context Protocol) open source che permette a Claude, ChatGPT e altri LLM di accedere ai dati ferroviari italiani in tempo reale: orari, ritardi, partenze, arrivi e tracciamento treni live tramite le API di Viaggiatreno e i dati NeTEx.",
          },
        },
        {
          "@type": "Question",
          name: "What is MCP Trenitalia?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "MCP Trenitalia is an open source MCP (Model Context Protocol) server that lets Claude, ChatGPT, and other LLMs access real-time Italian railway data: schedules, delays, departures, arrivals, and live train tracking via Viaggiatreno APIs and NeTEx data.",
          },
        },
        {
          "@type": "Question",
          name: "Quali tool MCP sono disponibili?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "MCP Trenitalia offre 5 tool: trenitalia_cerca_stazione (ricerca stazioni), trenitalia_monitora_partenze (partenze live), trenitalia_monitora_arrivi (arrivi live), trenitalia_traccia_treno (tracciamento treni) e trenitalia_orari_tra_stazioni (orari tra due stazioni con dati NeTEx + live).",
          },
        },
        {
          "@type": "Question",
          name: "Come si installa MCP Trenitalia?",
          acceptedAnswer: {
            "@type": "Answer",
            text: 'Si installa clonando la repository GitHub (git clone https://github.com/Fanfulla/MCP_Trenitalia), installando le dipendenze (pip install -r requirements.txt) e configurando il server MCP nel file claude_desktop_config.json.',
          },
        },
        {
          "@type": "Question",
          name: "Is MCP Trenitalia free to use?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Yes, MCP Trenitalia is completely free and open source, released under the MIT license. You can clone it from GitHub and use it with any MCP-compatible AI assistant.",
          },
        },
      ],
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it" className="dark" suppressHydrationWarning>
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#2563eb" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
