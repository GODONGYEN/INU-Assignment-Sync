const { contextBridge, ipcRenderer } = require("electron");

const api = {
  getConfig: () => ipcRenderer.invoke("config:get"),
  saveConfig: (updates) => ipcRenderer.invoke("config:save", updates),
  readLogFile: () => ipcRenderer.invoke("log:read"),
  clearLogFile: () => ipcRenderer.invoke("log:clear"),
  openLogFile: () => ipcRenderer.invoke("log:open"),
  openReadme: () => ipcRenderer.invoke("readme:open"),
  resetSyncHistory: () => ipcRenderer.invoke("sync:reset-history"),
  runSync: (payload) => ipcRenderer.invoke("sync:run", payload),
  onSyncOutput: (callback) => {
    const listener = (_, payload) => callback(payload);
    ipcRenderer.on("sync:output", listener);
    return () => ipcRenderer.removeListener("sync:output", listener);
  },
  onSyncExit: (callback) => {
    const listener = (_, payload) => callback(payload);
    ipcRenderer.on("sync:exit", listener);
    return () => ipcRenderer.removeListener("sync:exit", listener);
  },
};

try {
  contextBridge.exposeInMainWorld("inuSync", api);
  contextBridge.exposeInMainWorld("electronAPI", api);
  console.log("[preload] electronAPI exposed successfully");
} catch (error) {
  console.error("[preload] contextBridge expose failed", error);
}
