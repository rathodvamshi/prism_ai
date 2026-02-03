import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true, secure: false },
      "/auth": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        bypass: (req, res, options) => {
          // Allow HTML page requests to be handled by frontend router
          if (req.headers.accept && req.headers.accept.includes('text/html')) {
            return req.url;
          }
        }
      },
      "/chat": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        bypass: (req, res, options) => {
          if (req.headers.accept && req.headers.accept.includes('text/html')) {
            return req.url;
          }
        }
      },
      "/users": { target: "http://127.0.0.1:8000", changeOrigin: true, secure: false },
      "/tasks": { target: "http://127.0.0.1:8000", changeOrigin: true, secure: false },
      "/admin": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        bypass: (req, res, options) => {
          if (req.headers.accept && req.headers.accept.includes('text/html')) {
            return req.url;
          }
        }
      },
      "/api-keys": { target: "http://127.0.0.1:8000", changeOrigin: true, secure: false },
      "/static": { target: "http://127.0.0.1:8000", changeOrigin: true, secure: false },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true, secure: false },
    },
  },
  optimizeDeps: {
    include: ["react-window", "react-virtualized-auto-sizer"],
  },
  build: {
    commonjsOptions: {
      transformMixedEsModules: true,
      include: [/react-window/, /react-virtualized-auto-sizer/],
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
