import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { Providers } from "@/components/Providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Docling RAG Agent",
  description: "AI-powered document search with RAG and vector embeddings",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      {/*
        suppressHydrationWarning on both html and body tags prevents hydration
        warnings from browser extensions (e.g., Dashlane, password managers,
        ad blockers) that inject attributes like data-dashlane-rid, data-1p-ignore, etc.

        This is safe because:
        1. We're only suppressing warnings for these specific tags
        2. Extension-injected attributes don't affect app functionality
        3. Genuine hydration issues in our code will still be caught in child components

        See: https://react.dev/reference/react-dom/client/hydrateRoot#suppressing-unavoidable-hydration-mismatch-errors
      */}
      <body className={`${geistSans.variable} antialiased`} suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
