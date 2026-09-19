import nextConfig from "eslint-config-next";

const eslintConfig = [
  {
    ignores: ["node_modules/**", ".next/**", "out/**"],
  },
  ...nextConfig,
];

export default eslintConfig;
