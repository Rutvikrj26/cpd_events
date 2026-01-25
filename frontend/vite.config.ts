/// <reference types="vitest" />
import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { VitePWA } from "vite-plugin-pwa"

export default defineConfig({
    plugins: [
        react(),
        VitePWA({
            registerType: "autoUpdate",
            includeAssets: ["favicon.png", "apple-touch-icon.png", "icon-192.png", "icon-512.png"],
            manifest: {
                name: "Accredit",
                short_name: "Accredit",
                description: "Professional development event management and certification platform",
                theme_color: "#63945f",
                background_color: "#ffffff",
                display: "standalone",
                icons: [
                    {
                        src: "icon-192.png",
                        sizes: "192x192",
                        type: "image/png",
                        purpose: "any maskable"
                    },
                    {
                        src: "icon-512.png",
                        sizes: "512x512",
                        type: "image/png",
                        purpose: "any maskable"
                    }
                ]
            },
            workbox: {
                maximumFileSizeToCacheInBytes: 10 * 1024 * 1024,
                globPatterns: ["**/*.{js,css,html,ico,png,svg,woff,woff2}"],
                runtimeCaching: [
                    {
                        urlPattern: /^https:\/\/api\..*/i,
                        handler: "NetworkFirst",
                        options: {
                            cacheName: "api-cache",
                            expiration: {
                                maxEntries: 50,
                                maxAgeSeconds: 60 * 60 * 24 // 24 hours
                            },
                            cacheableResponse: {
                                statuses: [0, 200]
                            }
                        }
                    },
                    {
                        urlPattern: /\.(png|jpg|jpeg|svg|gif)$/,
                        handler: "CacheFirst",
                        options: {
                            cacheName: "images-cache",
                            expiration: {
                                maxEntries: 100,
                                maxAgeSeconds: 60 * 60 * 24 * 30 // 30 days
                            }
                        }
                    }
                ]
            }
        })
    ],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: ["./src/setupTests.ts"],
        include: ["src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    },
})
