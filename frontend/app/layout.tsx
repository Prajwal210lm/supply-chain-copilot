import type { Metadata } from "next";
import { Bricolage_Grotesque, Inter, Spline_Sans_Mono } from "next/font/google";
import "./globals.css";

const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const splineMono = Spline_Sans_Mono({
  variable: "--font-spline-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://supply-chain-copilot-nine.vercel.app"),
  title: "Supply Chain Copilot — grounded answers from operational data",
  description:
    "Every question about the data costs two days and an analyst. This copilot answers in seconds: plain-English questions become inspectable query specs, deterministic code computes every number. 96.7% measured spec accuracy, 100% adversarial refusal. All data synthetic; Mawarid Distribution is fictional.",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.png", type: "image/png" },
    ],
  },
  openGraph: {
    title: "Supply Chain Copilot",
    description:
      "Ask your supply chain a question. Get a grounded answer in seconds, not days. 96.7% measured spec accuracy; the model never writes SQL and never does arithmetic.",
    images: [{ url: "/og.png", width: 1200, height: 630 }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Supply Chain Copilot",
    description:
      "Plain-English questions over operational data, answered by tested code. The model never writes SQL and never does arithmetic.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body
        className={`${bricolage.variable} ${inter.variable} ${splineMono.variable} font-body`}
      >
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-100 focus:rounded-lg focus:bg-accent-deep focus:px-4 focus:py-2 focus:text-sm focus:text-white"
        >
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
