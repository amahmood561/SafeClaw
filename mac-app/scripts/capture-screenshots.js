const { app, BrowserWindow, ipcMain } = require('electron');
const fs = require('fs');
const os = require('os');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const outDir = path.join(root, 'docs', 'screenshots');

const defaults = {
  installDir: path.join(os.homedir(), 'safeclaw'),
  repoUrl: 'https://github.com/amahmood561/SafeClaw.git',
  ref: 'main',
  baseUrl: 'https://api.openai.com/v1',
  model: 'gpt-4.1-mini',
  workspace: './workspace',
  permissionProfile: 'readonly',
  approvalMode: 'ask',
  whatsappPort: '8080',
};

function registerHandlers() {
  ipcMain.handle('defaults', () => defaults);
  ipcMain.handle('load-env', () => ({}));
  ipcMain.handle('save-env', () => ({ ok: true, path: path.join(defaults.installDir, '.env') }));
  ipcMain.handle('install-safeclaw', () => ({ ok: true }));
  ipcMain.handle('safeclaw-command', () => ({ ok: true }));
  ipcMain.handle('open-path', () => ({ ok: true }));
  ipcMain.handle('open-logs', () => ({ ok: true }));
  ipcMain.handle('open-url', () => ({ ok: true }));
  ipcMain.handle('open-chat', () => ({ ok: true }));
  ipcMain.handle('list-sessions', () => ([
    { id: 'desktop', messages: 8, updatedAt: new Date().toISOString() },
    { id: 'whatsapp-test', messages: 3, updatedAt: new Date(Date.now() - 3600000).toISOString() },
    { id: 'project-audit', messages: 12, updatedAt: new Date(Date.now() - 7200000).toISOString() },
  ]));
  ipcMain.handle('rename-session', () => ({ ok: true }));
  ipcMain.handle('delete-session', () => ({ ok: true }));
  ipcMain.handle('approve-command', () => ({ ok: true }));
  ipcMain.handle('stop-command', () => ({ ok: true }));
}

async function capture(win, view, filename) {
  await win.webContents.executeJavaScript(`
    document.querySelectorAll('.view').forEach((node) => node.classList.toggle('active', node.id === '${view}'));
    document.querySelectorAll('.nav-item').forEach((node) => node.classList.toggle('active', node.dataset.view === '${view}'));
    document.getElementById('viewTitle').textContent = ${JSON.stringify(view === 'database' ? 'Databases' : view[0].toUpperCase() + view.slice(1))};
  `);
  await new Promise((resolve) => setTimeout(resolve, 250));
  const image = await win.capturePage();
  fs.writeFileSync(path.join(outDir, filename), image.toPNG());
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  registerHandlers();

  const win = new BrowserWindow({
    width: 1440,
    height: 1100,
    show: false,
    backgroundColor: '#f6f7f5',
    webPreferences: {
      preload: path.join(root, 'mac-app', 'src', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  await win.loadFile(path.join(root, 'mac-app', 'src', 'index.html'));
  await new Promise((resolve) => setTimeout(resolve, 500));

  await win.webContents.executeJavaScript(`
    document.getElementById('chatMessages').innerHTML = [
      '<div class="chat-message user" data-state="done"><div class="chat-role">You <span class="message-state">done</span></div><div class="chat-body">Summarize my SafeClaw setup and tell me what permissions are active.</div></div>',
      '<div class="chat-message assistant" data-state="running"><div class="chat-role">SafeClaw <span class="message-state">running</span></div><div class="chat-body">I can inspect the local configuration, session state, and workspace boundaries. Current profile: readonly.</div></div>'
    ].join('');
    document.getElementById('attachmentDrawer').open = true;
    document.getElementById('attachmentCount').textContent = '2';
    document.getElementById('chatAttachments').innerHTML = [
      '<div class="attachment-card file"><strong>README.md</strong><div class="attachment-meta">42.0 KB - content preview included</div><div class="attachment-actions"><select><option>Send as reference</option></select><button>Remove</button></div></div>',
      '<div class="attachment-card link"><strong>https://safestclaw.com/docs.html</strong><div class="attachment-meta">URL attachment</div><div class="attachment-actions"><select disabled><option>Send as reference</option></select><button>Remove</button></div></div>'
    ].join('');
  `);

  await capture(win, 'setup', 'mac-app-setup.png');
  await capture(win, 'chat', 'mac-app-chat.png');
  await capture(win, 'database', 'mac-app-databases.png');
}

app.whenReady().then(main).then(() => app.quit()).catch((error) => {
  console.error(error);
  app.quit();
  process.exitCode = 1;
});
