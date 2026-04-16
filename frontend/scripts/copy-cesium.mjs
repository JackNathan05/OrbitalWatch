/**
 * Copies Cesium static assets (Workers, ThirdParty, Assets, Widgets)
 * from node_modules into public/cesium/ so they're served at build time.
 *
 * Runs automatically via the "postinstall" npm script.
 */
import { cpSync, existsSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const cesiumBuild = join(root, "node_modules", "cesium", "Build", "Cesium");
const publicCesium = join(root, "public", "cesium");

if (!existsSync(cesiumBuild)) {
  console.log("Cesium not found in node_modules, skipping asset copy.");
  process.exit(0);
}

const dirs = ["Workers", "ThirdParty", "Assets", "Widgets"];

mkdirSync(publicCesium, { recursive: true });

for (const dir of dirs) {
  const src = join(cesiumBuild, dir);
  const dest = join(publicCesium, dir);
  if (existsSync(src)) {
    cpSync(src, dest, { recursive: true });
  }
}

console.log("Cesium assets copied to public/cesium/");
