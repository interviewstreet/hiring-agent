import "./globals.css";
import { Instrument_Serif, Archivo, JetBrains_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { ThemeProvider } from "@/ui/ThemeProvider";
import { SettingsProvider } from "@/ui/SettingsProvider";

const serif = Instrument_Serif({ weight: ["400"], subsets: ["latin"], variable: "--font-instrument-serif", display: "swap" });
const archivo = Archivo({ subsets: ["latin"], variable: "--font-archivo", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono", display: "swap" });

export const metadata = { title: "Hiring Agent", description: "Private, in-browser resume scoring" };

const themeBootstrap = `(function(){try{var t=localStorage.getItem('ha-theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);else document.documentElement.setAttribute('data-theme','light');}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${serif.variable} ${archivo.variable} ${mono.variable}`}>
      <head><script dangerouslySetInnerHTML={{ __html: themeBootstrap }} /></head>
      <body>
        <ThemeProvider>
          <SettingsProvider>{children}</SettingsProvider>
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  );
}
