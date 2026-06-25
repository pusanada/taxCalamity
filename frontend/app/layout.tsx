import type { Metadata } from 'next'
import './globals.css'
import { SessionProvider } from './lib/session-context'
import { Nav } from './components/Nav'

export const metadata: Metadata = {
  title: 'Chief Wealth Intelligence Platform',
  description: 'Production Multi-Agent Wealth Optimization & Compliance Engine',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body>
        <SessionProvider>
          <div className="min-h-screen pb-16 bg-[#080d16] text-[#f3f4f6] font-sans selection:bg-indigo-600 selection:text-white">
            <Nav />
            {children}
          </div>
        </SessionProvider>
      </body>
    </html>
  )
}
