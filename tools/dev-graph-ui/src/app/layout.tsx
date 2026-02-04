import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ChakraProvider } from '@chakra-ui/react';
import { QueryProvider } from '@/components/QueryProvider';
import ClientOnly from '@/components/ClientOnly';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Dev Graph - Knowledge Graph Visualization",
  description: "Standalone Developer Graph visualization tool for sprint documentation and Git history analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ClientOnly>
          <QueryProvider>
            <ChakraProvider>
              {children}
            </ChakraProvider>
          </QueryProvider>
        </ClientOnly>
      </body>
    </html>
  );
}
