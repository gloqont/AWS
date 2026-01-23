import "./globals.css";
import type { Metadata } from "next";
import { TutorialProvider } from "@/components/tutorial/TutorialContext";
import TutorialOverlay from "@/components/tutorial/TutorialOverlay";
import TutorialFlowManager from "@/components/tutorial/TutorialFlowManager";

export const metadata: Metadata = {
  title: "Advisor Dashboard",
  description: "Portfolio optimizer for financial advisers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
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
