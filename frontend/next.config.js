/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["cesium", "resium"],
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    config.resolve.fallback = { ...config.resolve.fallback, fs: false, path: false };
    return config;
  },
};
module.exports = nextConfig;
