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
  const nextTheme = isDark ? "light" : "dark";
  const nextLabel = nextTheme === "light" ? "Light" : "Dark";
  const nextIcon = nextTheme === "light" ? "☀️" : "🌙";

  return (
    <button
      type="button"
      onClick={() => setTheme(nextTheme)}
      className={[
        "inline-flex items-center gap-2 rounded-xl border border-border bg-card text-xs text-foreground hover:bg-muted",
        compact ? "px-2.5 py-2" : "px-3 py-2",
      ].join(" ")}
      aria-label={`Switch to ${nextLabel} mode`}
      title={`Switch to ${nextLabel} mode`}
    >
      <span className="text-base">{nextIcon}</span>
      {!compact && <span>{nextLabel}</span>}
    </button>
  );
}
