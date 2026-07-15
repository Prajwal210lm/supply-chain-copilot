import Approach from "@/components/Approach";
import Architecture from "@/components/Architecture";
import Conversation from "@/components/Conversation";
import Footer from "@/components/Footer";
import Hero from "@/components/Hero";
import Measurement from "@/components/Measurement";
import Nav from "@/components/Nav";
import Objections from "@/components/Objections";
import Problem from "@/components/Problem";
import Scope from "@/components/Scope";

export default function Home() {
  return (
    <div id="top">
      <Nav />
      <main id="main">
        <Hero />
        <div className="mx-auto max-w-6xl space-y-24 px-5 pb-24 sm:space-y-32 sm:px-8 sm:pb-32">
          <Problem />
          <Approach />
          <Conversation />
          <Architecture />
          <Measurement />
          <Scope />
          <Objections />
        </div>
      </main>
      <Footer />
    </div>
  );
}
