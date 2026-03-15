import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 180,
          height: 180,
          borderRadius: 36,
          background: "linear-gradient(135deg, #2563eb, #7c3aed)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 4,
        }}
      >
        <svg
          width="80"
          height="80"
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="4" y="3" width="16" height="14" rx="3" />
          <circle cx="9" cy="20" r="1.5" fill="white" />
          <circle cx="15" cy="20" r="1.5" fill="white" />
          <line x1="4" y1="17" x2="20" y2="17" />
          <line x1="9" y1="10" x2="9" y2="7" />
          <line x1="15" y1="10" x2="15" y2="7" />
        </svg>
        <span
          style={{
            color: "white",
            fontSize: 28,
            fontWeight: 800,
            fontFamily: "system-ui, sans-serif",
            letterSpacing: 2,
          }}
        >
          MCP
        </span>
      </div>
    ),
    { ...size }
  );
}
