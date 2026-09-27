import type { Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import type { Locale } from "@/lib/i18n";
import { THEME_COLORS } from "@/lib/site";
import "@/app/globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const siteViewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: THEME_COLORS.light },
    { media: "(prefers-color-scheme: dark)", color: THEME_COLORS.dark },
  ],
  colorScheme: "light dark",
};

export function SiteLayout({ children, locale }: { children: React.ReactNode; locale: Locale }) {
  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      {/* eslint-disable-next-line @next/next/no-head-element -- App Router root document: apply saved theme before paint. */}
      <head>
        <script dangerouslySetInnerHTML={{ __html: "try{var t=localStorage.getItem('theme');document.documentElement.classList.toggle('dark',t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches))}catch{}" }} />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
