import { LandingPage } from "@/components/landing-page";
import { pageMetadata, structuredData } from "@/lib/seo";

export const metadata = pageMetadata("en");

export default function Page() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: structuredData("en") }} />
      <LandingPage locale="en" />
    </>
  );
}
