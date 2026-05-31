const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('safeclaw', {
  defaults: () => ipcRenderer.invoke('defaults'),
  runtimeInfo: (settings) => ipcRenderer.invoke('runtime-info', settings),
  copyText: (text) => ipcRenderer.invoke('copy-text', text),
  loadEnv: (installDir) => ipcRenderer.invoke('load-env', installDir),
  saveEnv: (settings) => ipcRenderer.invoke('save-env', settings),
  install: (settings) => ipcRenderer.invoke('install-safeclaw', settings),
  command: (settings, args, title) => ipcRenderer.invoke('safeclaw-command', settings, args, title),
  openPath: (targetPath) => ipcRenderer.invoke('open-path', targetPath),
  openLogs: () => ipcRenderer.invoke('open-logs'),
  openUrl: (url) => ipcRenderer.invoke('open-url', url),
  openChat: (settings) => ipcRenderer.invoke('open-chat', settings),
  filePath: (file) => webUtils.getPathForFile(file),
  sessions: (settings) => ipcRenderer.invoke('list-sessions', settings),
  loadSession: (settings, sessionId) => ipcRenderer.invoke('load-session', settings, sessionId),
  renameSession: (settings, oldId, newId) => ipcRenderer.invoke('rename-session', settings, oldId, newId),
  deleteSession: (settings, sessionId) => ipcRenderer.invoke('delete-session', settings, sessionId),
  writeTaskStatus: (settings, payload) => ipcRenderer.invoke('write-task-status', settings, payload),
  approve: (answer) => ipcRenderer.invoke('approve-command', answer),
  stop: () => ipcRenderer.invoke('stop-command'),
  onOutput: (callback) => ipcRenderer.on('command-output', (_event, payload) => callback(payload)),
});
