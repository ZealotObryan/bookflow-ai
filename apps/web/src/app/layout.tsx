import type { Metadata } from "next";
import {AuthProvider} from "@/components/auth-provider";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "BookFlow AI — Your business, in flow", template: "%s · BookFlow AI" },
  description: "Appointments, customers and everyday operations in one connected workspace.",
  applicationName: "BookFlow AI",
};
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body><AuthProvider>{children}</AuthProvider></body></html>; }
