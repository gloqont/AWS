import "./globals.css";
import type { Metadata } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import { TutorialProvider } from "@/components/tutorial/TutorialContext";
import TutorialOverlay from "@/components/tutorial/TutorialOverlay";
import TutorialFlowManager from "@/components/tutorial/TutorialFlowManager";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ui",
});

export const metadata: Metadata = {
  title: "GLOQONT",
  description: "Portfolio optimizer for financial advisers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${ibmPlexSans.variable} font-sans antialiased`}
        style={{ fontFamily: "var(--font-ui), system-ui, sans-serif" }}
      >
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
