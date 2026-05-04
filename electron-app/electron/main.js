import { app, BrowserWindow, ipcMain, shell } from "electron";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, "..");
const PROJECT_ROOT = path.resolve(APP_ROOT, "..");
const ENV_PATH = path.join(PROJECT_ROOT, ".env");
const ENV_EXAMPLE_PATH = path.join(PROJECT_ROOT, ".env.example");
const README_PATH = path.join(PROJECT_ROOT, "README.md");
const DATA_DIR = path.join(PROJECT_ROOT, "data");
const LOGS_DIR = path.join(PROJECT_ROOT, "logs");
const DATABASE_PATH = path.join(DATA_DIR, "sync_state.sqlite3");
const LOG_FILE_PATH = path.join(LOGS_DIR, "app.log");
const DEV_SERVER_URL = "http://localhost:5173";
const IS_DEV_SERVER_MODE = process.argv.includes("--dev");

const DEFAULT_SETTINGS = {
  BASE_URL: "https://cyber.inu.ac.kr",
  CALENDAR_NAME: "INU 과제",
  CALENDAR_MONTHS_BACK: "2",
  CALENDAR_MONTHS_FORWARD: "6",
  INCLUDE_PAST_ASSIGNMENTS: "false",
  REMINDER_MINUTES: "1440,180",
  DRY_RUN: "true",
};

let mainWindow = null;
let syncProcess = null;

function ensureSupportFiles() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.mkdirSync(LOGS_DIR, { recursive: true });

  if (!fs.existsSync(ENV_PATH) && fs.existsSync(ENV_EXAMPLE_PATH)) {
    fs.copyFileSync(ENV_EXAMPLE_PATH, ENV_PATH);
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

function choosePythonExecutable() {
  const venvPython = path.join(PROJECT_ROOT, ".venv", "bin", "python");
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  return "python3";
}

function getConfigPayload() {
  ensureSupportFiles();
  return {
    ...DEFAULT_SETTINGS,
    ...readEnvFile(ENV_PATH),
  };
}

function getAppState() {
  return {
    envExists: fs.existsSync(ENV_PATH),
    logExists: fs.existsSync(LOG_FILE_PATH),
    databaseExists: fs.existsSync(DATABASE_PATH),
    pythonExecutable: choosePythonExecutable(),
    isSyncRunning: syncProcess !== null,
    projectRoot: PROJECT_ROOT,
    envPath: ENV_PATH,
    logPath: LOG_FILE_PATH,
    databasePath: DATABASE_PATH,
    readmePath: README_PATH,
  };
}

function sendSyncEvent(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

function createWindow() {
  console.log(`[electron] IS_DEV_SERVER_MODE=${IS_DEV_SERVER_MODE}`);
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1200,
    minHeight: 820,
    backgroundColor: "#020617",
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
    console.error(
      `[electron] did-fail-load code=${errorCode} description=${errorDescription} url=${validatedURL}`,
    );
  });

  mainWindow.webContents.on("console-message", (_event, level, message, line, sourceId) => {
    console.log(`[renderer:${level}] ${message} (${sourceId}:${line})`);
  });

  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    console.error(`[electron] render-process-gone reason=${details.reason} exitCode=${details.exitCode}`);
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
  console.log(`[electron] app root: ${APP_ROOT}`);
  console.log(`[electron] project root: ${PROJECT_ROOT}`);
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
  };
});

ipcMain.handle("config:save", async (_, updates) => {
  ensureSupportFiles();
  writeEnvFile(ENV_PATH, updates);
  return {
    ok: true,
    settings: getConfigPayload(),
  };
});

ipcMain.handle("log:read", async () => {
  ensureSupportFiles();
  if (!fs.existsSync(LOG_FILE_PATH)) {
    return "";
  }
  return fs.readFileSync(LOG_FILE_PATH, "utf8");
});

ipcMain.handle("log:clear", async () => {
  ensureSupportFiles();
  fs.writeFileSync(LOG_FILE_PATH, "", "utf8");
  return { ok: true };
});

ipcMain.handle("log:open", async () => {
  ensureSupportFiles();
  if (!fs.existsSync(LOG_FILE_PATH)) {
    fs.writeFileSync(LOG_FILE_PATH, "", "utf8");
  }
  return shell.openPath(LOG_FILE_PATH);
});

ipcMain.handle("readme:open", async () => {
  return shell.openPath(README_PATH);
});

ipcMain.handle("sync:reset-history", async () => {
  ensureSupportFiles();
  if (fs.existsSync(DATABASE_PATH)) {
    fs.unlinkSync(DATABASE_PATH);
  }
  return { ok: true };
});

ipcMain.handle("sync:run", async (_, payload = {}) => {
  if (syncProcess !== null) {
    return { ok: false, error: "이미 동기화가 실행 중입니다." };
  }

  ensureSupportFiles();

  const pythonExecutable = choosePythonExecutable();
  const scriptPath = path.join(PROJECT_ROOT, "main.py");
  const settings = {
    ...getConfigPayload(),
    ...(payload.settings || {}),
  };

  if (payload.forceDryRun) {
    settings.DRY_RUN = "true";
  }

  const childEnv = {
    ...process.env,
    ...settings,
    GUI_MODE: "true",
  };

  try {
    syncProcess = spawn(pythonExecutable, [scriptPath], {
      cwd: PROJECT_ROOT,
      env: childEnv,
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    syncProcess = null;
    return { ok: false, error: `Python 실행 실패: ${error.message}` };
  }

  sendSyncEvent("sync:output", `[INFO] Python 실행: ${pythonExecutable}`);

  const forwardOutput = (chunk) => {
    sendSyncEvent("sync:output", chunk.toString());
  };

  syncProcess.stdout.on("data", forwardOutput);
  syncProcess.stderr.on("data", forwardOutput);

  syncProcess.on("close", (code, signal) => {
    sendSyncEvent("sync:exit", { code, signal });
    syncProcess = null;
  });

  syncProcess.on("error", (error) => {
    sendSyncEvent("sync:output", `[ERROR] Python 프로세스 오류: ${error.message}\n`);
  });

  return { ok: true };
});
