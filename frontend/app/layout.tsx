import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/components/RoleContext';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'BitFortress | Bitcoin Corporate Multisig Treasury Platform',
  description: 'Enterprise Bitcoin multisignature treasury system with PSBT workflow, threshold policies, and cryptographic verification.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#030712] text-slate-100 min-h-screen antialiased`}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
