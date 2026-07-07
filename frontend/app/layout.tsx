import type { Metadata } from "next";
import { Fraunces, Instrument_Sans, Spline_Sans_Mono } from "next/font/google";
import "./globals.css";

// Three voices, one page: Fraunces speaks (headlines + the user's
// questions), Instrument Sans reports (narration, UI), Spline Sans Mono
// is the machine (specs, SQL, metadata). None of the three families
// appear in P1, P2, or P3.
const fraunces = Fraunces({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-fraunces",
  display: "swap",
});

const instrument = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap",
});

const splineMono = Spline_Sans_Mono({
  subsets: ["latin"],
  variable: "--font-spline-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://supply-chain-copilot.vercel.app"),
  title: "Supply Chain Copilot | Mawarid Distribution",
  description:
    "The answer is in the data; getting it out takes days. A conversational analyst for supply chain operations — plain-English questions become inspectable query specs, deterministic code computes the answers. 96.7% measured spec accuracy over four runs. All data synthetic; Mawarid Distribution is fictional.",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }, { url: "/favicon.png", sizes: "32x32" }],
  },
  openGraph: {
    title: "Supply Chain Copilot | Mawarid Distribution",
    description:
      "Ask in plain English, audit every answer. 96.7% measured spec accuracy over four independent runs.",
    images: [{ url: "/og.png", width: 1200, height: 630 }],
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${instrument.variable} ${splineMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <a href="#conversation" className="skip-link type-small">
          Skip to the demo conversation
        </a>
        {children}
      </body>
    </html>
  );
}
