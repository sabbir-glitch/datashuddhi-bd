import { DetectionScope } from "@/components/landing/DetectionScope";
import { FinalCta } from "@/components/landing/FinalCta";
import { Hero } from "@/components/landing/Hero";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Privacy } from "@/components/landing/Privacy";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { SiteHeader } from "@/components/landing/SiteHeader";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main id="main">
        <Hero />
        <HowItWorks />
        <DetectionScope />
        <Privacy />
        <FinalCta />
      </main>
      <SiteFooter />
    </>
  );
}
