import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Code Refactoring Agent",
  description: "AI-powered code refactoring assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>
        {children}
      </body>
    </html>
  );
}
