import type { Metadata } from "next";
import Link from "next/link";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "404 | Ciuff",
  robots: { index: false, follow: true },
};

export default function GlobalNotFound() {
  return (
    <html lang="it">
      <body style={{ background: "#080b14", color: "#f5f6fb", fontFamily: "system-ui, sans-serif", padding: "12vh 8vw", lineHeight: 1.6 }}>
        <main>
          <p>CIUFF / 404</p>
          <h1>Pagina non trovata</h1>
          <p lang="en">This page does not exist.</p>
          <p><Link href="/" style={{ color: "#9db8ff" }}>Torna alla home</Link> · <Link href="/en" lang="en" style={{ color: "#9db8ff" }}>English home</Link></p>
        </main>
      </body>
    </html>
  );
}
