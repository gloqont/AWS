import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { TutorialProvider } from "@/components/tutorial/TutorialContext";
import TutorialOverlay from "@/components/tutorial/TutorialOverlay";
import TutorialFlowManager from "@/components/tutorial/TutorialFlowManager";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "GLOQONT",
  description: "Portfolio optimizer for financial advisers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans`} style={{ fontFamily: 'var(--font-inter), system-ui, sans-serif' }}>
        <TutorialProvider>
          <TutorialOverlay>
            <TutorialFlowManager>
              {children}
            </TutorialFlowManager>
          </TutorialOverlay>
        </TutorialProvider>
      </body>
    </html>
  );
}
