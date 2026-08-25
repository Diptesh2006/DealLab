import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202a",
        steel: "#3d5a68",
        mint: "#2fbf9b",
        amber: "#d9972b",
        paper: "#f7f8f5"
      }
    },
  },
  plugins: [],
};

export default config;
