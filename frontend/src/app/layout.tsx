import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { AuthProvider } from "@/components/auth/auth-provider";
import { SessionBoundary } from "@/components/auth/session-boundary";
import { SiteFooter } from "@/components/layout/site-footer";
import { SiteHeader } from "@/components/layout/site-header";
import { themeInitScript } from "@/lib/theme";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "cyrillic"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin", "cyrillic"],
});

export const metadata: Metadata = {
  title: {
    default: "LoadLab — обучение нагрузочному тестированию",
    template: "%s — LoadLab",
  },
  description:
    "LoadLab — образовательная платформа для подготовки начинающих специалистов по нагрузочному тестированию: теория простым языком, практика и квизы.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ru"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
      // Класс темы выставляется скриптом до отрисовки, поэтому разметка
      // на сервере и в браузере может отличаться только этим классом.
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="flex min-h-full flex-col">
        <AuthProvider>
          <a
            href="#main"
            className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-primary-foreground focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
          >
            К содержанию
          </a>
          <SiteHeader />
          <main id="main" className="flex-1">
            <SessionBoundary>{children}</SessionBoundary>
          </main>
          <SiteFooter />
        </AuthProvider>
      </body>
    </html>
  );
}
