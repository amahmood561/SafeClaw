const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('safeclaw', {
  defaults: () => ipcRenderer.invoke('defaults'),
  loadEnv: (installDir) => ipcRenderer.invoke('load-env', installDir),
  saveEnv: (settings) => ipcRenderer.invoke('save-env', settings),
  install: (settings) => ipcRenderer.invoke('install-safeclaw', settings),
  command: (settings, args, title) => ipcRenderer.invoke('safeclaw-command', settings, args, title),
  openPath: (targetPath) => ipcRenderer.invoke('open-path', targetPath),
  openLogs: () => ipcRenderer.invoke('open-logs'),
  openUrl: (url) => ipcRenderer.invoke('open-url', url),
  openChat: (settings) => ipcRenderer.invoke('open-chat', settings),
  filePath: (file) => webUtils.getPathForFile(file),
  stop: () => ipcRenderer.invoke('stop-command'),
  onOutput: (callback) => ipcRenderer.on('command-output', (_event, payload) => callback(payload)),
});
