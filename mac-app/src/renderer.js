const $ = (id) => document.getElementById(id);

const permissionProfiles = [
  'readonly',
  'workspace-write',
  'network-allow',
  'shell-ask',
  'shell-allow',
  'messaging-allow',
  'db-readonly',
];

const approvalModes = ['ask', 'deny', 'auto'];
const textAttachmentLimit = 120000;
const textPreviewLimit = 40000;
const viewTitles = {
  setup: 'Setup',
  run: 'Run SafeClaw',
  chat: 'Chat',
  whatsapp: 'WhatsApp',
  database: 'Databases',
  logs: 'Output',
};

let activeChatResponse = null;
let chatAttachments = [];

function setOptions(select, values) {
  select.innerHTML = values.map((value) => `<option value="${value}">${value}</option>`).join('');
}

function settings() {
  return {
    installDir: $('installDir').value.trim(),
    repoUrl: $('repoUrl').value.trim(),
    ref: $('ref').value.trim(),
    apiKey: $('apiKey').value,
    baseUrl: $('baseUrl').value.trim(),
    model: $('model').value.trim(),
    workspace: $('workspace').value.trim(),
    permissionProfile: $('permissionProfile').value,
    approvalMode: $('approvalMode').value,
    allowShell: $('allowShell').checked,
    maxToolSteps: '6',
    sqliteDatabases: $('sqliteDatabases').value.trim(),
    whatsappPort: $('whatsappPort').value.trim(),
  };
}

function appendOutput(text) {
  const output = $('output');
  output.textContent += text;
  output.scrollTop = output.scrollHeight;
}

function setStatus(text, mode = 'idle') {
  const pill = $('statusPill');
  pill.textContent = text;
  pill.dataset.mode = mode;
}

function showView(name) {
  document.querySelectorAll('.view').forEach((view) => view.classList.toggle('active', view.id === name));
  document.querySelectorAll('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.view === name));
  $('viewTitle').textContent = viewTitles[name] || 'SafeClaw';
}

async function loadDefaults() {
  const defaults = await window.safeclaw.defaults();
  $('installDir').value = defaults.installDir;
  $('repoUrl').value = defaults.repoUrl;
  $('ref').value = defaults.ref;
  $('baseUrl').value = defaults.baseUrl;
  $('model').value = defaults.model;
  $('workspace').value = defaults.workspace;
  $('permissionProfile').value = defaults.permissionProfile;
  $('approvalMode').value = defaults.approvalMode;
  $('whatsappPort').value = defaults.whatsappPort;
}

async function loadEnv() {
  const env = await window.safeclaw.loadEnv($('installDir').value.trim());
  if (env.OPENAI_API_KEY) $('apiKey').value = env.OPENAI_API_KEY;
  if (env.OPENAI_BASE_URL) $('baseUrl').value = env.OPENAI_BASE_URL;
  if (env.OPENAI_MODEL) $('model').value = env.OPENAI_MODEL;
  if (env.WORKSPACE) $('workspace').value = env.WORKSPACE;
  if (env.SAFECLAW_PERMISSION_PROFILE) $('permissionProfile').value = env.SAFECLAW_PERMISSION_PROFILE;
  if (env.SAFECLAW_APPROVAL_MODE) $('approvalMode').value = env.SAFECLAW_APPROVAL_MODE;
  if (env.SAFECLAW_SQLITE_DATABASES) $('sqliteDatabases').value = env.SAFECLAW_SQLITE_DATABASES;
  $('allowShell').checked = (env.ALLOW_SHELL || '').toLowerCase() === 'true';
  appendOutput(`Loaded config from ${$('installDir').value}/.env\n`);
}

async function saveEnv() {
  const result = await window.safeclaw.saveEnv(settings());
  appendOutput(`Saved config: ${result.path}\n`);
}

async function runSafeClaw(args, title) {
  showView('logs');
  setStatus('Running', 'running');
  const result = await window.safeclaw.command(settings(), args, title);
  if (!result.ok) {
    appendOutput(`Error: ${result.error}\n`);
    setStatus('Idle');
  }
}

function chatArgs(command, extra = []) {
  const session = $('chatSession').value.trim() || 'desktop';
  const model = $('chatModel').value.trim();
  const permission = $('chatPermission').value;
  const args = [command, ...extra, '--session', session];
  if (model && ['run', 'chat'].includes(command)) args.push('--model', model);
  if (permission && ['run', 'chat', 'session-config'].includes(command)) args.push('--permission-profile', permission);
  return args;
}

function addChatMessage(role, text = '') {
  const empty = document.querySelector('.empty-chat');
  if (empty) empty.remove();
  const item = document.createElement('div');
  item.className = `chat-message ${role}`;
  const label = document.createElement('div');
  label.className = 'chat-role';
  label.textContent = role === 'user' ? 'You' : 'SafeClaw';
  const body = document.createElement('div');
  body.className = 'chat-body';
  body.textContent = text;
  item.append(label, body);
  $('chatMessages').appendChild(item);
  $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
  return body;
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return 'unknown size';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isLikelyTextFile(file) {
  if ((file.type || '').startsWith('text/')) return true;
  return /\.(csv|json|log|md|markdown|txt|yaml|yml|toml|xml|html|css|js|jsx|ts|tsx|py|rb|go|rs|java|c|cpp|h|hpp|sh|zsh|sql)$/i.test(file.name);
}

function renderAttachments() {
  const container = $('chatAttachments');
  container.innerHTML = '';
  container.hidden = chatAttachments.length === 0;
  for (const attachment of chatAttachments) {
    const chip = document.createElement('div');
    chip.className = `attachment-chip ${attachment.kind}`;
    const text = document.createElement('span');
    text.textContent = attachment.kind === 'link'
      ? attachment.url
      : `${attachment.name} (${formatBytes(attachment.size)})`;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => {
      chatAttachments = chatAttachments.filter((item) => item.id !== attachment.id);
      renderAttachments();
    });
    chip.append(text, remove);
    container.appendChild(chip);
  }
}

function attachmentPrompt() {
  if (!chatAttachments.length) return '';
  const blocks = chatAttachments.map((attachment, index) => {
    if (attachment.kind === 'link') {
      return [
        `Attachment ${index + 1}: URL`,
        `URL: ${attachment.url}`,
      ].join('\n');
    }

    const lines = [
      `Attachment ${index + 1}: file`,
      `Name: ${attachment.name}`,
      `Path: ${attachment.path || 'Unavailable from drag event'}`,
      `Type: ${attachment.type || 'unknown'}`,
      `Size: ${formatBytes(attachment.size)}`,
    ];
    if (attachment.preview) {
      lines.push('Content preview:', attachment.preview);
      if (attachment.truncated) lines.push('[Preview truncated]');
    } else {
      lines.push('Content preview: not included because the file is binary or too large.');
    }
    return lines.join('\n');
  });
  return `\n\nDropped attachments:\n${blocks.join('\n\n')}`;
}

function normalizeUrl(text) {
  const trimmed = text.trim();
  if (!trimmed) return '';
  try {
    const url = new URL(trimmed);
    return ['http:', 'https:'].includes(url.protocol) ? url.toString() : '';
  } catch (_error) {
    return '';
  }
}

async function addDroppedFiles(files) {
  for (const file of files) {
    const attachment = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      kind: 'file',
      name: file.name,
      path: window.safeclaw.filePath ? window.safeclaw.filePath(file) : file.path,
      type: file.type,
      size: file.size,
      preview: '',
      truncated: false,
    };
    if (isLikelyTextFile(file) && file.size <= textAttachmentLimit) {
      const text = await file.text();
      attachment.preview = text.slice(0, textPreviewLimit);
      attachment.truncated = text.length > textPreviewLimit;
    }
    chatAttachments.push(attachment);
  }
  renderAttachments();
}

function addDroppedLinks(text) {
  const urls = text
    .split(/\s+/)
    .map(normalizeUrl)
    .filter(Boolean);
  for (const url of urls) {
    chatAttachments.push({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      kind: 'link',
      url,
    });
  }
  renderAttachments();
}

async function handleChatDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  document.body.classList.remove('dragging-chat');

  const files = Array.from(event.dataTransfer.files || []);
  if (files.length) await addDroppedFiles(files);

  const uriList = event.dataTransfer.getData('text/uri-list');
  const plainText = event.dataTransfer.getData('text/plain');
  addDroppedLinks(uriList || plainText || '');
}

async function sendChat() {
  const text = $('chatInput').value.trim();
  const attachments = attachmentPrompt();
  if (!text && !attachments) return;
  const prompt = `${text || 'Please inspect these dropped attachments.'}${attachments}`;
  $('chatInput').value = '';
  chatAttachments = [];
  renderAttachments();
  addChatMessage('user', prompt);
  activeChatResponse = addChatMessage('assistant', '');
  setStatus('Chatting', 'running');
  const result = await window.safeclaw.command(settings(), chatArgs('run', [prompt]), 'Chat');
  if (!result.ok) {
    activeChatResponse.textContent = `Error: ${result.error}`;
    activeChatResponse = null;
    setStatus('Idle');
  }
}

function bindEvents() {
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.addEventListener('click', () => showView(item.dataset.view));
  });

  $('installBtn').addEventListener('click', async () => {
    showView('logs');
    setStatus('Installing', 'running');
    const result = await window.safeclaw.install(settings());
    if (!result.ok) appendOutput(`Error: ${result.error}\n`);
  });

  $('saveConfigBtn').addEventListener('click', saveEnv);
  $('loadConfigBtn').addEventListener('click', loadEnv);
  $('doctorBtn').addEventListener('click', () => runSafeClaw(['doctor'], 'Run Doctor'));
  $('openFolderBtn').addEventListener('click', () => window.safeclaw.openPath(settings().installDir));
  $('runTaskBtn').addEventListener('click', () => runSafeClaw(['run', $('taskInput').value], 'Run Task'));
  $('toolsBtn').addEventListener('click', () => runSafeClaw(['tools'], 'Show Tools'));
  $('sendChatBtn').addEventListener('click', sendChat);
  ['dragenter', 'dragover'].forEach((name) => {
    $('chat').addEventListener(name, (event) => {
      event.preventDefault();
      document.body.classList.add('dragging-chat');
    });
  });
  ['dragleave', 'drop'].forEach((name) => {
    $('chat').addEventListener(name, (event) => {
      if (name === 'drop') return handleChatDrop(event);
      if (!event.currentTarget.contains(event.relatedTarget)) {
        document.body.classList.remove('dragging-chat');
      }
    });
  });
  $('chatInput').addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') sendChat();
  });
  $('clearChatBtn').addEventListener('click', () => {
    $('chatMessages').innerHTML = '<div class="empty-chat"><strong>Start with a practical task.</strong><span>Ask SafeClaw to inspect setup, summarize files, plan changes, or explain what it can access.</span></div>';
  });
  $('chatStatusBtn').addEventListener('click', () => runSafeClaw(['status', '--session', $('chatSession').value.trim() || 'desktop'], 'Session Status'));
  $('chatMemoryBtn').addEventListener('click', () => runSafeClaw(['memory', '--session', $('chatSession').value.trim() || 'desktop'], 'Session Memory'));
  $('chatResetBtn').addEventListener('click', () => runSafeClaw(['reset', '--session', $('chatSession').value.trim() || 'desktop'], 'Reset Session'));
  $('openRepo').addEventListener('click', () => window.safeclaw.openUrl('https://github.com/amahmood561/SafeClaw'));
  $('twilioBtn').addEventListener('click', () => window.safeclaw.openUrl('https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn'));
  $('startWhatsappBtn').addEventListener('click', () => runSafeClaw(['whatsapp', '--host', '0.0.0.0', '--port', $('whatsappPort').value], 'Start WhatsApp Webhook'));
  $('whatsappSetupBtn').addEventListener('click', () => runSafeClaw(['whatsapp-setup'], 'WhatsApp Setup'));
  $('installServiceBtn').addEventListener('click', () => runSafeClaw(['service-install', '--port', $('whatsappPort').value], 'Install WhatsApp Service'));
  $('serviceStatusBtn').addEventListener('click', () => runSafeClaw(['service-status'], 'Service Status'));
  $('serviceStartBtn').addEventListener('click', () => runSafeClaw(['service-start'], 'Start Service'));
  $('serviceStopBtn').addEventListener('click', () => runSafeClaw(['service-stop'], 'Stop Service'));
  $('dbSaveBtn').addEventListener('click', saveEnv);
  $('dbListBtn').addEventListener('click', () => runSafeClaw(['db-list'], 'List Databases'));
  $('dbSchemaBtn').addEventListener('click', () => runSafeClaw(['db-schema', $('dbName').value], 'Database Schema'));
  $('dbTableBtn').addEventListener('click', () => runSafeClaw(['db-table', $('dbName').value, $('dbTable').value], 'Table Schema'));
  $('dbQueryBtn').addEventListener('click', () => runSafeClaw(['db-query', $('dbName').value, $('dbQuery').value, '--limit', $('dbLimit').value], 'Read-only Query'));
  $('clearOutputBtn').addEventListener('click', () => { $('output').textContent = ''; });
  $('stopBtn').addEventListener('click', async () => {
    const result = await window.safeclaw.stop();
    if (!result.ok) appendOutput(`${result.error}\n`);
  });
  $('openLogsBtn').addEventListener('click', () => window.safeclaw.openLogs());

  window.safeclaw.onOutput((payload) => {
    if (payload.type === 'start') setStatus('Running', 'running');
    if (payload.type === 'exit') setStatus(payload.code === 0 ? 'Done' : 'Failed', payload.code === 0 ? 'ok' : 'error');
    if (activeChatResponse && ['stdout', 'stderr', 'error'].includes(payload.type)) {
      activeChatResponse.textContent += payload.text;
      $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
    }
    if (activeChatResponse && payload.type === 'exit') {
      activeChatResponse = null;
    }
    appendOutput(payload.text);
  });
}

async function init() {
  setOptions($('permissionProfile'), permissionProfiles);
  setOptions($('chatPermission'), permissionProfiles);
  setOptions($('approvalMode'), approvalModes);
  await loadDefaults();
  await loadEnv().catch(() => {});
  bindEvents();
}

init();
