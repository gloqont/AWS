"use client";

import * as React from "react";
import { useTheme } from "next-themes";

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme, systemTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  const current = theme === "system" ? systemTheme : theme;
  const isDark = current === "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={[
        "inline-flex items-center gap-2 rounded-xl border border-border bg-card text-xs text-foreground hover:bg-muted",
        compact ? "px-2.5 py-2" : "px-3 py-2",
      ].join(" ")}
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      <span className="text-base">{isDark ? "🌙" : "☀️"}</span>
      {!compact && <span>{isDark ? "Dark" : "Light"}</span>}
    </button>
  );
}
