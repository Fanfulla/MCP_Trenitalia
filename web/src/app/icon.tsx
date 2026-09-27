import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 6,
          background: "linear-gradient(135deg, #2563eb, #7c3aed)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="5" y="3" width="14" height="14" rx="3" />
          <path d="M5 10h14M8 17l-2 4M16 17l2 4M8 21h8" />
          <circle cx="8.5" cy="13.5" r=".5" fill="white" />
          <circle cx="15.5" cy="13.5" r=".5" fill="white" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
