const { notarize } = require("@electron/notarize");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

function adHocSignApp(appPath, projectDir) {
  const entitlementsPath = path.join(projectDir, "build", "entitlements.mac.plist");
  const args = ["--force", "--deep", "--sign", "-", "--options", "runtime"];

  if (fs.existsSync(entitlementsPath)) {
    args.push("--entitlements", entitlementsPath);
  }

  args.push(appPath);

  console.log("[notarize] Apple Developer ID가 없어 ad-hoc 서명을 적용합니다.");
  execFileSync("codesign", args, { stdio: "inherit" });
  execFileSync("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appPath], {
    stdio: "inherit",
  });
}

module.exports = async function notarizeApp(context) {
  const { electronPlatformName, appOutDir, packager } = context;

  if (electronPlatformName !== "darwin") {
    return;
  }

  const appName = packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  if (process.env.SKIP_NOTARIZE === "true") {
    adHocSignApp(appPath, packager.projectDir);
    console.log("[notarize] SKIP_NOTARIZE=true 이므로 notarization을 건너뜁니다.");
    return;
  }

  if (process.env.APPLE_KEYCHAIN_PROFILE) {
    console.log("[notarize] keychain profile 방식으로 notarization을 진행합니다.");
    await notarize({
      appPath,
      keychainProfile: process.env.APPLE_KEYCHAIN_PROFILE,
    });
    return;
  }

  if (
    process.env.APPLE_ID &&
    process.env.APPLE_APP_SPECIFIC_PASSWORD &&
    process.env.APPLE_TEAM_ID
  ) {
    console.log("[notarize] Apple ID 방식으로 notarization을 진행합니다.");
    await notarize({
      appPath,
      appleId: process.env.APPLE_ID,
      appleIdPassword: process.env.APPLE_APP_SPECIFIC_PASSWORD,
      teamId: process.env.APPLE_TEAM_ID,
    });
    return;
  }

  if (
    process.env.APPLE_API_KEY &&
    process.env.APPLE_API_KEY_ID &&
    process.env.APPLE_API_ISSUER
  ) {
    console.log("[notarize] App Store Connect API key 방식으로 notarization을 진행합니다.");
    await notarize({
      appPath,
      appleApiKey: process.env.APPLE_API_KEY,
      appleApiKeyId: process.env.APPLE_API_KEY_ID,
      appleApiIssuer: process.env.APPLE_API_ISSUER,
    });
    return;
  }

  adHocSignApp(appPath, packager.projectDir);
  console.log("[notarize] Apple 자격증명이 없어 notarization을 건너뜁니다.");
};
