/** @type {import('next').NextConfig} */
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = dirname(fileURLToPath(import.meta.url));

const nextConfig = {
  agentRules: false,
  turbopack: {
    root: projectRoot,
  },
};

export default nextConfig;
