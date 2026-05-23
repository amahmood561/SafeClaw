const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const DEFAULTS = {
  repoUrl: 'https://github.com/amahmood561/SafeClaw.git',
  ref: 'main',
  installDir: path.join(os.homedir(), 'safeclaw'),
  baseUrl: 'https://api.openai.com/v1',
  model: 'gpt-4.1-mini',
  workspace: './workspace',
  permissionProfile: 'readonly',
  approvalMode: 'ask',
  maxToolSteps: '6',
  whatsappPort: '8080',
};

let mainWindow;
let runningProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 820,
    minWidth: 980,
    minHeight: 700,
    title: 'SafeClaw',
    show: false,
    backgroundColor: '#f6f7f5',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
    app.focus({ steal: true });
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

function safeclawBin(installDir) {
  return path.join(installDir, '.venv', 'bin', 'safeclaw');
}

function commandEnv(installDir) {
  return {
    ...process.env,
    SAFECLAW_EVENT_STREAM: 'true',
    PATH: `${path.join(installDir, '.venv', 'bin')}:/opt/homebrew/bin:/usr/local/bin:${process.env.PATH || ''}`,
  };
}

function workspacePath(settings = {}) {
  const installDir = settings.installDir || DEFAULTS.installDir;
  const workspace = settings.workspace || DEFAULTS.workspace;
  const resolved = path.resolve(installDir, workspace);
  return path.isAbsolute(workspace) ? workspace : resolved;
}

function safeId(sessionId) {
  const cleaned = String(sessionId || '')
    .split('')
    .map((ch) => /[A-Za-z0-9._-]/.test(ch) ? ch : '_')
    .join('');
  return cleaned || 'default';
}

function sessionFile(settings, sessionId) {
  return path.join(workspacePath(settings), '.safeclaw_sessions', `${safeId(sessionId)}.json`);
}

function memoryFile(settings, sessionId) {
  return path.join(workspacePath(settings), '.safeclaw_memory', `${safeId(sessionId)}.json`);
}

function listSessionFiles(settings = {}) {
  const dir = path.join(workspacePath(settings), '.safeclaw_sessions');
  if (!fs.existsSync(dir)) {
    return [];
  }
  return fs.readdirSync(dir)
    .filter((name) => name.endsWith('.json'))
    .map((name) => {
      const filePath = path.join(dir, name);
      let data = {};
      try {
        data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      } catch (_error) {
        data = {};
      }
      const stat = fs.statSync(filePath);
      return {
        id: data.id || path.basename(name, '.json'),
        model: data.model || '',
        permissionProfile: data.permission_profile || '',
        messages: Array.isArray(data.messages) ? data.messages.length : 0,
        updatedAt: data.updated_at || stat.mtime.toISOString(),
      };
    })
    .sort((a, b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));
}

function parseEnvFile(envPath) {
  if (!fs.existsSync(envPath)) {
    return {};
  }
  const values = {};
  for (const line of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [key, ...rest] = line.split('=');
    values[key.trim()] = rest.join('=').trim();
  }
  return values;
}

function send(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

function runCommand({ id, title, command, args = [], cwd }) {
  if (runningProcess) {
    return { ok: false, error: 'Another SafeClaw command is already running.' };
  }

  send('command-output', { id, type: 'start', text: `==> ${title}\n$ ${[command, ...args].join(' ')}\n` });

  runningProcess = spawn(command, args, {
    cwd,
    env: commandEnv(cwd),
    shell: false,
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  runningProcess.stdout.on('data', (data) => {
    send('command-output', { id, type: 'stdout', text: data.toString() });
  });

  runningProcess.stderr.on('data', (data) => {
    send('command-output', { id, type: 'stderr', text: data.toString() });
  });

  runningProcess.on('error', (error) => {
    send('command-output', { id, type: 'error', text: `${error.message}\n` });
    runningProcess = null;
  });

  runningProcess.on('close', (code) => {
    send('command-output', { id, type: 'exit', text: `\n[exit ${code}]\n`, code });
    runningProcess = null;
  });

  return { ok: true };
}

function safeclawCommand(settings, args) {
  const bin = safeclawBin(settings.installDir);
  if (fs.existsSync(bin)) {
    return { command: bin, args };
  }
  return { command: 'python3', args: ['-m', 'safeclaw.cli', ...args] };
}

ipcMain.handle('defaults', () => DEFAULTS);

ipcMain.handle('load-env', (_event, installDir) => {
  const envPath = path.join(installDir, '.env');
  return parseEnvFile(envPath);
});

ipcMain.handle('save-env', (_event, settings) => {
  fs.mkdirSync(settings.installDir, { recursive: true });
  const envPath = path.join(settings.installDir, '.env');
  const existing = parseEnvFile(envPath);
  const apiKey = settings.apiKey || existing.OPENAI_API_KEY || '';
  const twilioSid = settings.twilioSid || existing.TWILIO_ACCOUNT_SID || '';
  const twilioToken = settings.twilioToken || existing.TWILIO_AUTH_TOKEN || '';
  const twilioFrom = settings.twilioFrom || existing.TWILIO_WHATSAPP_FROM || 'whatsapp:+14155238886';
  const allowedSenders = settings.allowedSenders || existing.SAFECLAW_ALLOWED_SENDERS || '';
  const telegramToken = settings.telegramToken || existing.TELEGRAM_BOT_TOKEN || '';
  const allowedTelegramUsers = settings.allowedTelegramUsers || existing.SAFECLAW_ALLOWED_TELEGRAM_USERS || '';
  const content = [
    '# Use OpenAI-compatible API endpoint',
    `SAFECLAW_PROVIDER_PRESET=${settings.providerPreset || 'custom'}`,
    `OPENAI_API_KEY=${apiKey}`,
    `OPENAI_BASE_URL=${settings.baseUrl || DEFAULTS.baseUrl}`,
    `OPENAI_MODEL=${settings.model || DEFAULTS.model}`,
    '',
    '# Agent settings',
    `WORKSPACE=${settings.workspace || DEFAULTS.workspace}`,
    `ALLOW_SHELL=${settings.allowShell ? 'true' : 'false'}`,
    `SAFECLAW_PERMISSION_PROFILE=${settings.permissionProfile || DEFAULTS.permissionProfile}`,
    `SAFECLAW_APPROVAL_MODE=${settings.approvalMode || DEFAULTS.approvalMode}`,
    `MAX_TOOL_STEPS=${settings.maxToolSteps || DEFAULTS.maxToolSteps}`,
    '',
    '# Optional read-only SQLite databases.',
    `SAFECLAW_SQLITE_DATABASES=${settings.sqliteDatabases || ''}`,
    '',
    '# Optional Twilio WhatsApp outbound support.',
    `TWILIO_ACCOUNT_SID=${twilioSid}`,
    `TWILIO_AUTH_TOKEN=${twilioToken}`,
    `TWILIO_WHATSAPP_FROM=${twilioFrom}`,
    `SAFECLAW_ALLOWED_SENDERS=${allowedSenders}`,
    '',
    '# Optional Telegram phone access.',
    `TELEGRAM_BOT_TOKEN=${telegramToken}`,
    `SAFECLAW_ALLOWED_TELEGRAM_USERS=${allowedTelegramUsers}`,
    '',
  ].join('\n');
  fs.writeFileSync(envPath, content, { mode: 0o600 });
  return { ok: true, path: envPath };
});

ipcMain.handle('install-safeclaw', (_event, settings) => {
  const script = [
    'curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh',
    '|',
    `SAFECLAW_DIR=${JSON.stringify(settings.installDir)}`,
    `SAFECLAW_REPO=${JSON.stringify(settings.repoUrl || DEFAULTS.repoUrl)}`,
    `SAFECLAW_REF=${JSON.stringify(settings.ref || DEFAULTS.ref)}`,
    'bash',
  ].join(' ');
  return runCommand({
    id: 'install',
    title: 'Install / Update SafeClaw',
    command: 'bash',
    args: ['-lc', script],
    cwd: os.homedir(),
  });
});

ipcMain.handle('safeclaw-command', (_event, settings, commandArgs, title = 'SafeClaw command') => {
  const resolved = safeclawCommand(settings, commandArgs);
  return runCommand({
    id: commandArgs[0] || 'safeclaw',
    title,
    command: resolved.command,
    args: resolved.args,
    cwd: settings.installDir,
  });
});

ipcMain.handle('open-path', (_event, targetPath) => {
  fs.mkdirSync(targetPath, { recursive: true });
  shell.openPath(targetPath);
  return { ok: true };
});

ipcMain.handle('open-logs', () => {
  const logs = path.join(os.homedir(), 'Library', 'Logs', 'SafeClaw');
  fs.mkdirSync(logs, { recursive: true });
  shell.openPath(logs);
  return { ok: true };
});

ipcMain.handle('open-url', (_event, url) => {
  shell.openExternal(url);
  return { ok: true };
});

ipcMain.handle('open-chat', (_event, settings) => {
  const bin = safeclawBin(settings.installDir);
  const command = `cd ${JSON.stringify(settings.installDir)} && ${JSON.stringify(bin)} chat`;
  spawn('osascript', ['-e', `tell application "Terminal" to do script ${JSON.stringify(command)}`], {
    detached: true,
    stdio: 'ignore',
  }).unref();
  return { ok: true };
});

ipcMain.handle('list-sessions', (_event, settings) => {
  const sessions = listSessionFiles(settings);
  if (!sessions.some((item) => item.id === 'desktop')) {
    sessions.unshift({ id: 'desktop', model: '', permissionProfile: '', messages: 0, updatedAt: '' });
  }
  return sessions;
});

ipcMain.handle('load-session', (_event, settings, sessionId) => {
  const filePath = sessionFile(settings, sessionId);
  if (!fs.existsSync(filePath)) {
    return {
      ok: true,
      session: {
        id: sessionId || 'desktop',
        model: '',
        permissionProfile: '',
        messages: [],
        updatedAt: '',
      },
    };
  }
  try {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return {
      ok: true,
      session: {
        id: data.id || sessionId,
        model: data.model || '',
        permissionProfile: data.permission_profile || '',
        messages: Array.isArray(data.messages) ? data.messages : [],
        updatedAt: data.updated_at || '',
      },
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

ipcMain.handle('rename-session', (_event, settings, oldId, newId) => {
  const oldPath = sessionFile(settings, oldId);
  const newPath = sessionFile(settings, newId);
  if (!newId || !String(newId).trim()) {
    return { ok: false, error: 'Session name is required.' };
  }
  if (!fs.existsSync(oldPath)) {
    return { ok: false, error: `Session not found: ${oldId}` };
  }
  fs.mkdirSync(path.dirname(newPath), { recursive: true });
  if (fs.existsSync(newPath)) {
    return { ok: false, error: `Session already exists: ${newId}` };
  }
  const data = JSON.parse(fs.readFileSync(oldPath, 'utf8'));
  data.id = newId;
  fs.writeFileSync(newPath, JSON.stringify(data, null, 2));
  fs.unlinkSync(oldPath);
  const oldMemory = memoryFile(settings, oldId);
  const newMemory = memoryFile(settings, newId);
  if (fs.existsSync(oldMemory)) {
    fs.mkdirSync(path.dirname(newMemory), { recursive: true });
    fs.renameSync(oldMemory, newMemory);
  }
  return { ok: true };
});

ipcMain.handle('delete-session', (_event, settings, sessionId) => {
  fs.rmSync(sessionFile(settings, sessionId), { force: true });
  fs.rmSync(memoryFile(settings, sessionId), { force: true });
  return { ok: true };
});

ipcMain.handle('approve-command', (_event, answer) => {
  if (!runningProcess || !runningProcess.stdin || runningProcess.stdin.destroyed) {
    return { ok: false, error: 'No command is waiting for approval.' };
  }
  runningProcess.stdin.write(`${answer}\n`);
  return { ok: true };
});

ipcMain.handle('stop-command', () => {
  if (runningProcess) {
    runningProcess.kill();
    runningProcess = null;
    return { ok: true };
  }
  return { ok: false, error: 'No command is running.' };
});
