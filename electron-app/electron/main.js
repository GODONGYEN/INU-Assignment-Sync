import { app, BrowserWindow, ipcMain, shell } from "electron";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

app.setName("INU Assignment Sync");

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, "..");
const PROJECT_ROOT = path.resolve(APP_ROOT, "..");
const DEV_SERVER_URL = "http://localhost:5173";
const IS_DEV_SERVER_MODE = process.argv.includes("--dev");

const DEFAULT_SETTINGS = {
  LOGIN_URL: "https://cyber.inu.ac.kr/login.php",
  ASSIGNMENTS_URL: "https://cyber.inu.ac.kr/calendar/view.php?view=month",
  BASE_URL: "https://cyber.inu.ac.kr",
  USE_MANUAL_LOGIN: "true",
  GUI_MODE: "true",
  HEADLESS: "false",
  SLOW_MO_MS: "0",
  PAGE_TIMEOUT_MS: "15000",
  LOGIN_WAIT_TIMEOUT_MS: "180000",
  CALENDAR_NAME: "INU 과제",
  EVENT_DURATION_MINUTES: "30",
  TIMEZONE: "Asia/Seoul",
  DATABASE_PATH: "data/sync_state.sqlite3",
  CALENDAR_MONTHS_BACK: "2",
  CALENDAR_MONTHS_FORWARD: "6",
  INCLUDE_PAST_ASSIGNMENTS: "false",
  REMINDER_MINUTES: "1440,180",
  DRY_RUN: "true",
};

let mainWindow = null;
let syncProcess = null;

function isPackagedRuntime() {
  return app.isPackaged && !IS_DEV_SERVER_MODE;
}

function getPackagedCodeRootCandidates() {
  if (!process.resourcesPath) {
    return [];
  }

  return [
    path.join(process.resourcesPath, "python"),
    path.join(process.resourcesPath, "app.asar.unpacked", "python"),
    process.resourcesPath,
  ];
}

function hasPythonBackend(candidatePath) {
  return fs.existsSync(path.join(candidatePath, "main.py")) && fs.existsSync(path.join(candidatePath, "src"));
}

function getCodeRoot() {
  if (!isPackagedRuntime()) {
    return PROJECT_ROOT;
  }

  for (const candidate of getPackagedCodeRootCandidates()) {
    if (hasPythonBackend(candidate)) {
      return candidate;
    }
  }

  // Return the expected packaged location so diagnostics can show the exact path that is missing.
  return path.join(process.resourcesPath, "python");
}

function getSupportRoot() {
  return app.getPath("userData");
}

function getSupportPaths() {
  const supportRoot = getSupportRoot();
  return {
    supportRoot,
    envPath: path.join(supportRoot, ".env"),
    dataDir: path.join(supportRoot, "data"),
    logsDir: path.join(supportRoot, "logs"),
    databasePath: path.join(supportRoot, "data", "sync_state.sqlite3"),
    logFilePath: path.join(supportRoot, "logs", "app.log"),
    venvDir: path.join(supportRoot, ".venv"),
    browsersDir: path.join(supportRoot, "ms-playwright"),
  };
}

function getCodePaths() {
  const codeRoot = getCodeRoot();
  return {
    codeRoot,
    scriptPath: path.join(codeRoot, "main.py"),
    envExamplePath: path.join(codeRoot, ".env.example"),
    requirementsPath: path.join(codeRoot, "requirements.txt"),
    readmePath: path.join(codeRoot, "README.md"),
  };
}

function validatePythonBackendFiles() {
  const codePaths = getCodePaths();
  const missing = [];

  for (const [label, filePath] of [
    ["main.py", codePaths.scriptPath],
    ["requirements.txt", codePaths.requirementsPath],
    [".env.example", codePaths.envExamplePath],
  ]) {
    if (!fs.existsSync(filePath)) {
      missing.push(`${label}: ${filePath}`);
    }
  }

  if (!fs.existsSync(path.join(codePaths.codeRoot, "src"))) {
    missing.push(`src/: ${path.join(codePaths.codeRoot, "src")}`);
  }

  return {
    ok: missing.length === 0,
    missing,
    codeRoot: codePaths.codeRoot,
  };
}

function appendAppLog(text) {
  try {
    const { logsDir, logFilePath } = getSupportPaths();
    fs.mkdirSync(logsDir, { recursive: true });
    fs.appendFileSync(logFilePath, text, "utf8");
  } catch {
    // Logging must never break the app itself.
  }
}

function ensureSupportFiles() {
  const supportPaths = getSupportPaths();
  const codePaths = getCodePaths();
  fs.mkdirSync(supportPaths.dataDir, { recursive: true });
  fs.mkdirSync(supportPaths.logsDir, { recursive: true });

  if (!fs.existsSync(supportPaths.envPath) && fs.existsSync(codePaths.envExamplePath)) {
    fs.copyFileSync(codePaths.envExamplePath, supportPaths.envPath);
  }

  if (!fs.existsSync(supportPaths.envPath)) {
    writeEnvFile(supportPaths.envPath, DEFAULT_SETTINGS);
  }
}

function readEnvFile(envPath) {
  if (!fs.existsSync(envPath)) {
    return {};
  }

  const content = fs.readFileSync(envPath, "utf8");
  const values = {};

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const separatorIndex = line.indexOf("=");
    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    values[key] = value;
  }

  return values;
}

function writeEnvFile(envPath, updates) {
  const updateKeys = Object.keys(updates);
  const existing = fs.existsSync(envPath) ? fs.readFileSync(envPath, "utf8").split(/\r?\n/) : [];
  const nextLines = [];
  const seenKeys = new Set();

  for (const rawLine of existing) {
    const separatorIndex = rawLine.indexOf("=");
    if (separatorIndex === -1) {
      nextLines.push(rawLine);
      continue;
    }

    const key = rawLine.slice(0, separatorIndex).trim();
    if (!updateKeys.includes(key)) {
      nextLines.push(rawLine);
      continue;
    }

    nextLines.push(`${key}=${updates[key]}`);
    seenKeys.add(key);
  }

  for (const key of updateKeys) {
    if (!seenKeys.has(key)) {
      nextLines.push(`${key}=${updates[key]}`);
    }
  }

  fs.writeFileSync(envPath, `${nextLines.join("\n").replace(/\n+$/, "")}\n`, "utf8");
}

function executableExists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function choosePythonExecutable({ allowSystemFallback = true } = {}) {
  const supportPaths = getSupportPaths();
  const userVenvPython3 = path.join(supportPaths.venvDir, "bin", "python3");
  const userVenvPython = path.join(supportPaths.venvDir, "bin", "python");
  const projectVenvPython3 = path.join(PROJECT_ROOT, ".venv", "bin", "python3");
  const projectVenvPython = path.join(PROJECT_ROOT, ".venv", "bin", "python");

  for (const candidate of [userVenvPython3, userVenvPython, projectVenvPython3, projectVenvPython]) {
    if (executableExists(candidate)) {
      return candidate;
    }
  }

  return allowSystemFallback ? "python3" : "";
}

function createPythonEnv(settings = {}) {
  const supportPaths = getSupportPaths();
  const codePaths = getCodePaths();
  const existingPythonPath = process.env.PYTHONPATH ? `${codePaths.codeRoot}:${process.env.PYTHONPATH}` : codePaths.codeRoot;

  return {
    ...process.env,
    ...settings,
    GUI_MODE: "true",
    USE_MANUAL_LOGIN: "true",
    PYTHONPATH: existingPythonPath,
    INU_SYNC_APP_DATA_DIR: supportPaths.supportRoot,
    INU_SYNC_ENV_PATH: supportPaths.envPath,
    INU_SYNC_DATA_DIR: supportPaths.dataDir,
    INU_SYNC_LOGS_DIR: supportPaths.logsDir,
    PLAYWRIGHT_BROWSERS_PATH: supportPaths.browsersDir,
  };
}

function runProcess(command, args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: options.cwd ?? getCodeRoot(),
      env: options.env ?? createPythonEnv(),
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      stdout += text;
      options.onOutput?.(text);
    });

    child.stderr.on("data", (chunk) => {
      const text = chunk.toString();
      stderr += text;
      options.onOutput?.(text);
    });

    child.on("error", (error) => {
      resolve({ ok: false, code: null, stdout, stderr: `${stderr}${error.message}` });
    });

    child.on("close", (code) => {
      resolve({ ok: code === 0, code, stdout, stderr });
    });
  });
}

async function checkPythonDependencies() {
  const backend = validatePythonBackendFiles();
  if (!backend.ok) {
    return {
      ok: false,
      pythonExecutable: choosePythonExecutable(),
      message: "앱 안의 Python 백엔드 파일을 찾지 못했습니다. 앱을 다시 빌드하거나 최신 앱으로 교체해 주세요.",
      stdout: "",
      stderr: `Python backend missing in ${backend.codeRoot}\n${backend.missing.join("\n")}`,
    };
  }

  const pythonExecutable = choosePythonExecutable();
  const code = [
    "import sys",
    "missing=[]",
    "mods=['dotenv','playwright']",
    "for mod in mods:",
    "    try: __import__(mod)",
    "    except Exception: missing.append(mod)",
    "print(sys.executable)",
    "raise SystemExit(1 if missing else 0)",
  ].join("\n");
  const result = await runProcess(pythonExecutable, ["-c", code], {
    env: createPythonEnv(),
  });

  return {
    ok: result.ok,
    pythonExecutable,
    message: result.ok
      ? "Python 의존성이 준비되어 있습니다."
      : "Python 의존성이 아직 준비되지 않았습니다. 앱에서 설치를 실행해 주세요.",
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

async function installPythonDependencies() {
  const supportPaths = getSupportPaths();
  const codePaths = getCodePaths();
  const backend = validatePythonBackendFiles();
  if (!backend.ok) {
    const details = `Python backend missing in ${backend.codeRoot}\n${backend.missing.join("\n")}`;
    sendSyncOutput(`[ERROR] ${details}\n`);
    return {
      ok: false,
      error: "앱에 포함된 Python 파일을 찾지 못했습니다.",
      details: `${details}\n\n해결: electron-app에서 npm run pack 또는 npm run dist로 앱을 다시 빌드한 뒤 새로 생성된 앱을 실행해 주세요.`,
    };
  }

  const basePython = executableExists(path.join(supportPaths.venvDir, "bin", "python3"))
    ? path.join(supportPaths.venvDir, "bin", "python3")
    : "python3";

  fs.mkdirSync(supportPaths.supportRoot, { recursive: true });

  if (!fs.existsSync(path.join(supportPaths.venvDir, "bin", "python3"))) {
    sendSyncOutput("[INFO] 앱 전용 Python 가상환경을 생성합니다.\n");
    const venvResult = await runProcess(basePython, ["-m", "venv", supportPaths.venvDir], {
      cwd: supportPaths.supportRoot,
      env: process.env,
      onOutput: sendSyncOutput,
    });
    if (!venvResult.ok) {
      return { ok: false, error: "Python 가상환경 생성에 실패했습니다.", details: venvResult.stderr };
    }
  }

  const venvPython = path.join(supportPaths.venvDir, "bin", "python3");
  const commands = [
    [venvPython, ["-m", "ensurepip", "--upgrade"], "pip 준비"],
    [venvPython, ["-m", "pip", "install", "--upgrade", "pip<25"], "pip 업그레이드"],
    [venvPython, ["-m", "pip", "install", "-r", codePaths.requirementsPath], "Python 패키지 설치"],
    [venvPython, ["-m", "playwright", "install", "chromium"], "Playwright Chromium 설치"],
  ];

  for (const [command, args, label] of commands) {
    sendSyncOutput(`[INFO] ${label} 중...\n`);
    const result = await runProcess(command, args, {
      cwd: codePaths.codeRoot,
      env: createPythonEnv(),
      onOutput: sendSyncOutput,
    });
    if (!result.ok) {
      return { ok: false, error: `${label}에 실패했습니다.`, details: result.stderr };
    }
  }

  return { ok: true, pythonExecutable: venvPython };
}

function getConfigPayload() {
  ensureSupportFiles();
  return {
    ...DEFAULT_SETTINGS,
    ...readEnvFile(getSupportPaths().envPath),
  };
}

function getAppState() {
  const supportPaths = getSupportPaths();
  const codePaths = getCodePaths();
  return {
    envExists: fs.existsSync(supportPaths.envPath),
    logExists: fs.existsSync(supportPaths.logFilePath),
    databaseExists: fs.existsSync(supportPaths.databasePath),
    pythonExecutable: choosePythonExecutable(),
    isPackaged: isPackagedRuntime(),
    isSyncRunning: syncProcess !== null,
    codeRoot: codePaths.codeRoot,
    supportRoot: supportPaths.supportRoot,
    envPath: supportPaths.envPath,
    logPath: supportPaths.logFilePath,
    databasePath: supportPaths.databasePath,
    readmePath: codePaths.readmePath,
  };
}

function sendSyncEvent(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

function sendSyncOutput(text) {
  appendAppLog(text);
  sendSyncEvent("sync:output", text);
}

function createWindow() {
  console.log(`[electron] IS_DEV_SERVER_MODE=${IS_DEV_SERVER_MODE}`);
  console.log(`[electron] isPackagedRuntime=${isPackagedRuntime()}`);
  console.log(`[electron] code root=${getCodeRoot()}`);
  console.log(`[electron] support root=${getSupportRoot()}`);

  mainWindow = new BrowserWindow({
    width: 1320,
    height: 900,
    minWidth: 1080,
    minHeight: 760,
    backgroundColor: "#111827",
    titleBarStyle: "hiddenInset",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const rendererPath = path.join(APP_ROOT, "dist", "index.html");
  console.log(`[electron] preload path: ${path.join(__dirname, "preload.js")}`);
  console.log(`[electron] renderer dist path: ${rendererPath}`);
  console.log(`[electron] dev server url: ${DEV_SERVER_URL}`);

  mainWindow.webContents.on("did-finish-load", () => {
    console.log("[electron] renderer did-finish-load");
  });

  mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
    console.error(`[electron] did-fail-load code=${errorCode} description=${errorDescription} url=${validatedURL}`);
  });

  mainWindow.webContents.on("console-message", (_event, level, message, line, sourceId) => {
    console.log(`[renderer:${level}] ${message} (${sourceId}:${line})`);
  });

  if (IS_DEV_SERVER_MODE) {
    mainWindow.loadURL(DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(rendererPath);
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });
}

app.whenReady().then(() => {
  ensureSupportFiles();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

ipcMain.handle("config:get", async () => {
  return {
    settings: getConfigPayload(),
    state: getAppState(),
    dependencies: await checkPythonDependencies(),
  };
});

ipcMain.handle("config:save", async (_, updates) => {
  ensureSupportFiles();
  writeEnvFile(getSupportPaths().envPath, updates);
  return {
    ok: true,
    settings: getConfigPayload(),
    state: getAppState(),
  };
});

ipcMain.handle("dependencies:check", async () => {
  return checkPythonDependencies();
});

ipcMain.handle("dependencies:install", async () => {
  return installPythonDependencies();
});

ipcMain.handle("log:read", async () => {
  ensureSupportFiles();
  const { logFilePath } = getSupportPaths();
  if (!fs.existsSync(logFilePath)) {
    return "";
  }
  return fs.readFileSync(logFilePath, "utf8");
});

ipcMain.handle("log:clear", async () => {
  ensureSupportFiles();
  fs.writeFileSync(getSupportPaths().logFilePath, "", "utf8");
  return { ok: true };
});

ipcMain.handle("log:open", async () => {
  ensureSupportFiles();
  const { logFilePath } = getSupportPaths();
  if (!fs.existsSync(logFilePath)) {
    fs.writeFileSync(logFilePath, "", "utf8");
  }
  return shell.openPath(logFilePath);
});

ipcMain.handle("support:open", async () => {
  ensureSupportFiles();
  return shell.openPath(getSupportRoot());
});

ipcMain.handle("readme:open", async () => {
  const { readmePath } = getCodePaths();
  if (fs.existsSync(readmePath)) {
    return shell.openPath(readmePath);
  }
  return shell.openExternal("https://github.com/");
});

ipcMain.handle("sync:reset-history", async () => {
  ensureSupportFiles();
  const { databasePath } = getSupportPaths();
  if (fs.existsSync(databasePath)) {
    fs.unlinkSync(databasePath);
  }
  return { ok: true };
});

ipcMain.handle("sync:run", async (_, payload = {}) => {
  if (syncProcess !== null) {
    return { ok: false, error: "이미 동기화가 실행 중입니다." };
  }

  ensureSupportFiles();

  const backend = validatePythonBackendFiles();
  if (!backend.ok) {
    const details = `Python backend missing in ${backend.codeRoot}\n${backend.missing.join("\n")}`;
    sendSyncOutput(`[ERROR] ${details}\n`);
    return {
      ok: false,
      error: "앱에 포함된 Python 실행 파일을 찾지 못했습니다. 최신 앱으로 다시 빌드해 주세요.",
      details,
    };
  }

  const dependencies = await checkPythonDependencies();
  if (!dependencies.ok) {
    return {
      ok: false,
      error: "Python 의존성이 준비되지 않았습니다. 먼저 'Python 의존성 설치/확인'을 실행해 주세요.",
    };
  }

  const pythonExecutable = choosePythonExecutable({ allowSystemFallback: false }) || choosePythonExecutable();
  const { scriptPath, codeRoot } = getCodePaths();
  const settings = {
    ...getConfigPayload(),
    ...(payload.settings || {}),
  };

  if (payload.forceDryRun) {
    settings.DRY_RUN = "true";
  }

  try {
    syncProcess = spawn(pythonExecutable, [scriptPath], {
      cwd: codeRoot,
      env: createPythonEnv(settings),
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    syncProcess = null;
    return { ok: false, error: `Python 실행 실패: ${error.message}` };
  }

  sendSyncOutput(`[INFO] Python 실행: ${pythonExecutable}\n`);
  sendSyncOutput(`[INFO] 앱 데이터 위치: ${getSupportRoot()}\n`);

  const forwardOutput = (chunk) => {
    sendSyncOutput(chunk.toString());
  };

  syncProcess.stdout.on("data", forwardOutput);
  syncProcess.stderr.on("data", forwardOutput);

  syncProcess.on("close", (code, signal) => {
    sendSyncEvent("sync:exit", { code, signal });
    syncProcess = null;
  });

  syncProcess.on("error", (error) => {
    sendSyncOutput(`[ERROR] Python 프로세스 오류: ${error.message}\n`);
  });

  return { ok: true };
});
