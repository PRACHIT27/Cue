import { Inter, Playfair_Display, Space_Grotesk } from "next/font/google";
import "./globals.css";

const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const display = Space_Grotesk({ subsets: ["latin"], weight: ["500", "700"], variable: "--font-display" });
const serif = Playfair_Display({ subsets: ["latin"], style: ["italic"], weight: ["600"], variable: "--font-serif" });

export const metadata = {
  title: "Cue",
  description: "Cue matches musicians with the shows, films, games, podcasts and brands whose audiences already love their sound.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${body.variable} ${display.variable} ${serif.variable}`}>{children}</body>
    </html>
  );
}
