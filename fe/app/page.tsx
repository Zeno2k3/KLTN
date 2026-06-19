import LandingNav from "./_components/LandingNav";
import LandingHero from "./_components/LandingHero";
import StatsSection from "./_components/StatsSection";
import FeaturesSection from "./_components/FeaturesSection";
import HowItWorksSection from "./_components/HowItWorksSection";
import PartnersMarquee from "./_components/PartnersMarquee";
import ReviewsSection from "./_components/ReviewsSection";
import LandingCTA from "./_components/LandingCTA";
import LandingFooter from "./_components/LandingFooter";

export default function LandingPage() {
  return (
    <div style={{ fontFamily: "var(--font-body)", color: "var(--text-body)", background: "var(--surface-page)", overflowX: "hidden" }}>
      <LandingNav />
      <LandingHero />
      <StatsSection />
      <FeaturesSection />
      <HowItWorksSection />
      <PartnersMarquee />
      <ReviewsSection />
      <LandingCTA />
      <LandingFooter />
    </div>
  );
}
