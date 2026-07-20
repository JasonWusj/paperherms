import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        paper: "#f7f5ef",
        moss: "#5b715a",
        rust: "#a95735",
        bluegray: "#526b7a"
      }
    }
  },
  plugins: []
};

export default config;
