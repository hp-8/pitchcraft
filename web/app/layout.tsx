import type { Metadata } from "next";
import { Archivo, Geist_Mono } from "next/font/google";
import "./globals.css";

const archivo = Archivo({ variable: "--font-archivo", subsets: ["latin"], weight: ["400", "500", "600", "700", "800", "900"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://pitchcraft.harshpatadia.com"),
  title: { default: "Pitchcraft", template: "%s · Pitchcraft" },
  description: "Turn lead lists into audited, redesigned, ready-to-send pitches.",
  openGraph: { siteName: "Pitchcraft", type: "website", locale: "en_US" },
  twitter: { card: "summary_large_image" },
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${archivo.variable} ${geistMono.variable}`}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
