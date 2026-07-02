import type { ReactNode } from 'react';
import './globals.css';

export const metadata = {
  title: 'RaeburnAI Meeting Intelligence',
  description: 'Meeting intelligence for decisions, actions, owners and workflow writebacks.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
