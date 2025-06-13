import type { Metadata } from "next";
// import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Provider } from '@/components/ui/provider'
import { ColorModeScript } from '@chakra-ui/react'

// const geistSans = Geist({
//   variable: "--font-geist-sans",
//   subsets: ["latin"],
// });

// const geistMono = Geist_Mono({
//   variable: "--font-geist-mono",
//   subsets: ["latin"],
// });

export const metadata: Metadata = {
  title: "Pixel Detective - AI-Powered Image Search",
  description: "Your intelligent image search and management platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ColorModeScript initialColorMode="system" />
        <Provider>{children}</Provider>
      </body>
    </html>
  );
}
