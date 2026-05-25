import type { Metadata } from "next";
import { CopilotKit } from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Account Assistant",
  description: "Chapter 7 CrewAI + CopilotKit account assistant",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          agent="account_assistant"
          enableInspector={false}
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
