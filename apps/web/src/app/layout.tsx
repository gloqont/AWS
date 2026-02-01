import "./globals.css";
import type { Metadata } from "next";
import { TutorialProvider } from "@/components/tutorial/TutorialContext";
import TutorialOverlay from "@/components/tutorial/TutorialOverlay";
import TutorialFlowManager from "@/components/tutorial/TutorialFlowManager";
import { ThemeProvider } from "@/components/theme-provider";

export const metadata: Metadata = {
  title: "GLOQONT Dashboard",
  description: "GLOQONT advisor console",
  icons: {
    icon: "/gloqont-logo.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-background text-foreground">
        <ThemeProvider>
          <TutorialProvider>
            <TutorialOverlay>
              <TutorialFlowManager>
                {children}
              </TutorialFlowManager>
            </TutorialOverlay>
          </TutorialProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
