import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { CssBaseline } from '@mui/material'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'BuergerAI - Bürgerleistungen identifizieren',
  description: 'Finde heraus, welche Leistungen dir in deiner Situation zustehen',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="de">
      <body className={inter.className}>
        <CssBaseline />
        {children}
      </body>
    </html>
  )
}
