import BeforeAfter from "@/components/BeforeAfter";
import ConversationThread from "@/components/ConversationThread";
import Footer from "@/components/Footer";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import Measurement from "@/components/Measurement";
import Nav from "@/components/Nav";
import Objections from "@/components/Objections";
import ScopeHonesty from "@/components/ScopeHonesty";
import Reveal from "@/components/ui/Reveal";

export default function Home() {
  return (
    <>
      <Nav />
      <main id="main" className="flex flex-col">
        <Hero />
        <div className="flex flex-col gap-24 sm:gap-32">
          <Reveal>
            <BeforeAfter />
          </Reveal>
          <Reveal>
            <ConversationThread />
          </Reveal>
          <HowItWorks />
          <Reveal>
            <Measurement />
          </Reveal>
          <Reveal>
            <Objections />
          </Reveal>
          <Reveal>
            <ScopeHonesty />
          </Reveal>
        </div>
        <Footer />
      </main>
    </>
  );
}
