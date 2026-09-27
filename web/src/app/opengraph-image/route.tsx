import { ImageResponse } from "next/og";

export const dynamic = "force-static";
const size = { width: 1200, height: 630 };

export function GET() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#080b14", color: "#f5f7ff", padding: "64px 72px", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <svg width="54" height="54" viewBox="0 0 32 32" fill="none">
            <rect x="7" y="3" width="18" height="23" rx="6" stroke="#7da4ff" strokeWidth="2.5" />
            <path d="M7 15h18M16 3v12M10 26l-3 4m15-4 3 4" stroke="#7da4ff" strokeWidth="2.5" />
            <circle cx="12" cy="21" r="1.5" fill="#7da4ff" /><circle cx="20" cy="21" r="1.5" fill="#7da4ff" />
          </svg>
          <span style={{ fontSize: 52, fontWeight: 700, letterSpacing: -2 }}>Ciuff</span>
        </div>
        <span style={{ color: "#aab7d6", fontSize: 22 }}>ciuff.org</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        <div style={{ color: "#7da4ff", fontSize: 26, letterSpacing: 4 }}>MODEL CONTEXT PROTOCOL</div>
        <div style={{ fontSize: 82, fontWeight: 700, letterSpacing: -4, lineHeight: 1.1 }}>Trenitalia + Italo</div>
        <div style={{ color: "#c2cbe0", fontSize: 34 }}>Timetables and live train information for your AI.</div>
      </div>
      <div style={{ display: "flex", gap: 18, fontSize: 23, color: "#c2cbe0" }}>
        <span>Free &amp; open source</span><span style={{ color: "#4a649b" }}>•</span><span>Self-hosted</span><span style={{ color: "#4a649b" }}>•</span><span>11 MCP tools</span>
      </div>
    </div>,
    size,
  );
}
