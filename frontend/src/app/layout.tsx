import type { Metadata } from "next";
// import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Inter } from "next/font/google";
import { Provider } from "@/components/ui/provider";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClientProviders } from './client-providers';

// const geistSans = Geist({
//   variable: "--font-geist-sans",
//   subsets: ["latin"],
// });

// const geistMono = Geist_Mono({
//   variable: "--font-geist-mono",
//   subsets: ["latin"],
// });

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Vibe Coder",
  description: "Your intelligent image search and management platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <ClientProviders>
          <Provider>
            {children}
          </Provider>
        </ClientProviders>
      </body>
    </html>
  );
}
