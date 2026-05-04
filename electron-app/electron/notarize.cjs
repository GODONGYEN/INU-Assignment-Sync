const { notarize } = require("@electron/notarize");

module.exports = async function notarizeApp(context) {
  const { electronPlatformName, appOutDir, packager } = context;

  if (electronPlatformName !== "darwin") {
    return;
  }

  const appName = packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  if (process.env.SKIP_NOTARIZE === "true") {
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

  console.log("[notarize] Apple 자격증명이 없어 notarization을 건너뜁니다.");
};
