import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import {AuthProvider} from "@/components/auth-provider";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "BookFlow Ai — Your business, in flow", template: "%s · BookFlow Ai" },
  description: "Appointments, customers and everyday operations in one connected workspace.",
  applicationName: "BookFlow Ai",
  icons: { icon: "/icon.svg", shortcut: "/icon.svg", apple: "/icon.svg" },
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://bookflow-ai-sigma.vercel.app"),
  openGraph: { title: "BookFlow Ai — Your business, in flow", description: "Appointments, customers and everyday operations in one connected workspace.", siteName: "BookFlow Ai", type: "website" },
  twitter: { card: "summary_large_image", title: "BookFlow Ai — Your business, in flow", description: "Appointments, customers and everyday operations in one connected workspace." },
};
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body><AuthProvider>{children}</AuthProvider><Analytics /><SpeedInsights /></body></html>; }
