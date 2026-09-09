import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  // BASE_PATH='/ro-edu-registry/' on GitHub Pages, '/' elsewhere (Cloudflare Pages, local dev)
  base: process.env.BASE_PATH || '/',
  plugins: [react(), tailwindcss()],
})
