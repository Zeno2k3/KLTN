import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Khớp alias '@/...' của tsconfig (gốc fe/).
    alias: [{ find: /^@\//, replacement: fileURLToPath(new URL("./", import.meta.url)) }],
  },
  test: {
    environment: "jsdom",
    include: ["app/**/*.{test,spec}.{ts,tsx}"],
  },
});
