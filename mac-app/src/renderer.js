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
const hugeFileLimit = 2 * 1024 * 1024;
const viewTitles = {
  setup: 'Setup',
  run: 'Run SafeClaw',
  chat: 'Chat',
  whatsapp: 'WhatsApp',
  database: 'Databases',
  logs: 'Output',
};

let activeChatResponse = null;
let activeChatItem = null;
let lastChatPrompt = '';
let chatAttachments = [];
let lastMemoryTarget = '';

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

function chatSessionId() {
  return $('chatSession').value.trim() || 'desktop';
}

function workspaceDisplay() {
  return $('workspace').value.trim() || './workspace';
}

function updateChatContext() {
  if (!$('chatContextBar')) return;
  const model = $('chatModel').value.trim() || $('model').value.trim() || 'default model';
  const profile = $('chatPermission').value || $('permissionProfile').value || 'readonly';
  const approval = $('approvalMode').value || 'ask';
  $('chatContextBar').innerHTML = [
    ['Workspace', workspaceDisplay()],
    ['Permission', profile],
    ['Approval', approval],
    ['Model', model],
  ].map(([label, value]) => `<span><strong>${label}</strong>${value}</span>`).join('');
}

function showView(name) {
  document.querySelectorAll('.view').forEach((view) => view.classList.toggle('active', view.id === name));
  document.querySelectorAll('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.view === name));
  $('viewTitle').textContent = viewTitles[name] || 'SafeClaw';
  if (name === 'chat') updateChatContext();
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
  const session = chatSessionId();
  const model = $('chatModel').value.trim();
  const permission = $('chatPermission').value;
  const args = [command, ...extra, '--session', session];
  if (model && ['run', 'chat'].includes(command)) args.push('--model', model);
  if (permission && ['run', 'chat', 'session-config'].includes(command)) args.push('--permission-profile', permission);
  return args;
}

function setMessageState(item, state) {
  if (!item) return;
  item.dataset.state = state;
  const stateNode = item.querySelector('.message-state');
  if (stateNode) stateNode.textContent = state;
}

function addChatMessage(role, text = '', state = 'done') {
  const empty = document.querySelector('.empty-chat');
  if (empty) empty.remove();
  const item = document.createElement('div');
  item.className = `chat-message ${role}`;
  item.dataset.state = state;
  const label = document.createElement('div');
  label.className = 'chat-role';
  label.textContent = role === 'user' ? 'You' : 'SafeClaw';
  const stateNode = document.createElement('span');
  stateNode.className = 'message-state';
  stateNode.textContent = state;
  label.appendChild(stateNode);
  const body = document.createElement('div');
  body.className = 'chat-body';
  body.textContent = text;
  item.append(label, body);
  $('chatMessages').appendChild(item);
  $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
  return { item, body };
}

function addResultBlock(parent, type, text) {
  const block = document.createElement('pre');
  block.className = `result-block ${type}`;
  block.textContent = text;
  parent.appendChild(block);
  $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
  return block;
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

function isOutsideWorkspace(filePath) {
  if (!filePath) return false;
  const workspace = workspaceDisplay();
  if (!workspace || workspace === './workspace') return false;
  return !filePath.startsWith(workspace);
}

function renderAttachments() {
  const container = $('chatAttachments');
  const drawer = $('attachmentDrawer');
  const count = $('attachmentCount');
  container.innerHTML = '';
  drawer.open = chatAttachments.length > 0;
  count.textContent = String(chatAttachments.length);
  $('dropHint').textContent = chatAttachments.length
    ? `${chatAttachments.length} attachment${chatAttachments.length === 1 ? '' : 's'} ready to send.`
    : 'Files and links become removable attachments before sending.';
  for (const attachment of chatAttachments) {
    const card = document.createElement('div');
    card.className = `attachment-card ${attachment.kind}`;
    if (attachment.warning) card.classList.add('warning');
    const title = document.createElement('strong');
    title.textContent = attachment.kind === 'link' ? attachment.url : attachment.name;
    const meta = document.createElement('div');
    meta.className = 'attachment-meta';
    meta.textContent = attachment.kind === 'link'
      ? 'URL attachment'
      : `${formatBytes(attachment.size)} - ${attachment.preview ? 'content preview included' : 'sent as local reference'}`;
    const mode = document.createElement('select');
    mode.setAttribute('aria-label', `Send mode for ${attachment.name || attachment.url}`);
    mode.innerHTML = '<option value="reference">Send as reference</option><option value="include">Include contents</option>';
    mode.value = attachment.mode || 'reference';
    mode.disabled = attachment.kind === 'link' || (!attachment.preview && attachment.kind === 'file');
    mode.addEventListener('change', () => {
      attachment.mode = mode.value;
    });
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => {
      chatAttachments = chatAttachments.filter((item) => item.id !== attachment.id);
      renderAttachments();
    });
    card.append(title, meta);
    if (attachment.warning) {
      const warning = document.createElement('div');
      warning.className = 'attachment-warning';
      warning.textContent = attachment.warning;
      card.appendChild(warning);
    }
    const actions = document.createElement('div');
    actions.className = 'attachment-actions';
    actions.append(mode, remove);
    card.appendChild(actions);
    container.appendChild(card);
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
      `Send mode: ${attachment.mode || 'reference'}`,
    ];
    if (attachment.warning) {
      lines.push(`Warning: ${attachment.warning}`);
    }
    if (attachment.preview && attachment.mode === 'include') {
      lines.push('Content preview:', attachment.preview);
      if (attachment.truncated) lines.push('[Preview truncated]');
    } else {
      lines.push('Content preview: not included. Treat this as a local file reference unless the user asks to inspect it.');
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
      mode: 'reference',
      warning: '',
    };
    if (isLikelyTextFile(file) && file.size <= textAttachmentLimit) {
      const text = await file.text();
      attachment.preview = text.slice(0, textPreviewLimit);
      attachment.truncated = text.length > textPreviewLimit;
    }
    if (file.size > hugeFileLimit) {
      attachment.warning = `Huge file warning: ${formatBytes(file.size)}. Send as reference unless you really need content included.`;
    } else if (isOutsideWorkspace(attachment.path)) {
      attachment.warning = 'Outside workspace warning: SafeClaw may not be allowed to read this path.';
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

function formatTime(value) {
  if (!value) return 'new';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

async function refreshSessions() {
  const list = $('sessionList');
  const current = chatSessionId();
  list.innerHTML = '';
  const sessions = await window.safeclaw.sessions(settings()).catch(() => [{ id: 'desktop', updatedAt: '' }]);
  for (const session of sessions) {
    const item = document.createElement('button');
    item.className = 'session-item';
    item.type = 'button';
    item.classList.toggle('active', session.id === current);
    item.innerHTML = `<strong>${session.id}</strong><span>${formatTime(session.updatedAt)} · ${session.messages || 0} messages</span>`;
    item.addEventListener('click', () => {
      $('chatSession').value = session.id;
      updateChatContext();
      refreshSessions();
    });
    list.appendChild(item);
  }
}

function currentSessionArgs(command, extra = []) {
  return [command, ...extra, '--session', chatSessionId()];
}

function renderApprovalCard(kind, detail) {
  const tray = $('approvalTray');
  tray.hidden = false;
  tray.innerHTML = '';
  const card = document.createElement('div');
  card.className = 'approval-card';
  card.innerHTML = `
    <span class="tag">Needs approval</span>
    <h3>${kind}</h3>
    <p>${detail}</p>
    <pre>${detail}</pre>
  `;
  const actions = document.createElement('div');
  actions.className = 'button-row wrap';
  [
    ['Allow once', 'y'],
    ['Deny', 'n'],
    ['Always allow for this session', 'y'],
  ].forEach(([label, answer]) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.addEventListener('click', async () => {
      await window.safeclaw.approve(answer);
      tray.hidden = true;
      tray.innerHTML = '';
      if (activeChatItem) setMessageState(activeChatItem, answer === 'y' ? 'running' : 'stopped');
    });
    actions.appendChild(button);
  });
  card.appendChild(actions);
  tray.appendChild(card);
  if (activeChatItem) setMessageState(activeChatItem, 'needs approval');
  setStatus('Needs approval', 'running');
}

function detectApproval(text) {
  const lower = text.toLowerCase();
  if (!lower.includes('approval') && !lower.includes('allow this action') && !lower.includes('[y/n]') && !lower.includes('[y/n]')) {
    return;
  }
  let kind = 'Action approval';
  if (lower.includes('shell')) kind = 'Shell command';
  if (lower.includes('write') || lower.includes('patch') || lower.includes('file')) kind = 'File change';
  if (lower.includes('url') || lower.includes('network') || lower.includes('fetch')) kind = 'Network fetch';
  if (lower.includes('whatsapp') || lower.includes('message')) kind = 'WhatsApp send';
  renderApprovalCard(kind, text.trim().slice(0, 1200));
}

function resetEmptyChat() {
  $('chatMessages').innerHTML = `
    <div class="empty-chat">
      <strong>Start with a practical task.</strong>
      <span>Ask SafeClaw to inspect setup, summarize files, plan changes, or explain what it can access. Drop files or links here to include them.</span>
      <div class="starter-actions" aria-label="Suggested starter actions">
        <button data-starter="Run doctor">Run doctor</button>
        <button data-starter="Explain my config">Explain my config</button>
        <button data-starter="Check WhatsApp setup">Check WhatsApp setup</button>
        <button data-starter="Summarize this folder">Summarize this folder</button>
        <button data-starter="Inspect dropped file">Inspect dropped file</button>
      </div>
    </div>`;
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
  lastChatPrompt = prompt;
  lastMemoryTarget = text || prompt.slice(0, 300);
  $('chatInput').value = '';
  chatAttachments = [];
  renderAttachments();
  const userMessage = addChatMessage('user', prompt, 'queued');
  setMessageState(userMessage.item, 'done');
  const assistantMessage = addChatMessage('assistant', '', 'running');
  activeChatItem = assistantMessage.item;
  activeChatResponse = assistantMessage.body;
  setStatus('Chatting', 'running');
  const result = await window.safeclaw.command(settings(), chatArgs('run', [prompt]), 'Chat');
  if (!result.ok) {
    activeChatResponse.textContent = '';
    addResultBlock(activeChatResponse, 'error', `Error: ${result.error}`);
    setMessageState(activeChatItem, 'failed');
    activeChatResponse = null;
    activeChatItem = null;
    setStatus('Idle');
  }
  await refreshSessions();
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
  $('retryChatBtn').addEventListener('click', () => {
    if (!lastChatPrompt) return;
    $('chatInput').value = lastChatPrompt;
    sendChat();
  });
  $('stopChatBtn').addEventListener('click', async () => {
    const result = await window.safeclaw.stop();
    if (!result.ok) appendOutput(`${result.error}\n`);
    if (activeChatItem) setMessageState(activeChatItem, 'stopped');
    activeChatResponse = null;
    activeChatItem = null;
    setStatus('Stopped', 'error');
  });
  $('refreshSessionsBtn').addEventListener('click', refreshSessions);
  $('renameSessionBtn').addEventListener('click', async () => {
    const oldId = chatSessionId();
    const newId = prompt('Rename session', oldId);
    if (!newId || newId === oldId) return;
    const result = await window.safeclaw.renameSession(settings(), oldId, newId);
    if (!result.ok) return appendOutput(`Rename failed: ${result.error}\n`);
    $('chatSession').value = newId;
    updateChatContext();
    refreshSessions();
  });
  $('deleteSessionBtn').addEventListener('click', async () => {
    const session = chatSessionId();
    if (!confirm(`Delete session "${session}"?`)) return;
    await window.safeclaw.deleteSession(settings(), session);
    $('chatSession').value = 'desktop';
    updateChatContext();
    refreshSessions();
  });
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
  $('chatMessages').addEventListener('click', (event) => {
    const starter = event.target.closest('[data-starter]');
    if (!starter) return;
    const text = starter.dataset.starter;
    if (text === 'Run doctor') return runSafeClaw(['doctor'], 'Run Doctor');
    $('chatInput').value = text;
    sendChat();
  });
  $('clearChatBtn').addEventListener('click', resetEmptyChat);
  ['workspace', 'model', 'chatModel', 'chatPermission', 'permissionProfile', 'approvalMode'].forEach((id) => {
    $(id).addEventListener('input', updateChatContext);
    $(id).addEventListener('change', updateChatContext);
  });
  $('chatSession').addEventListener('input', () => {
    updateChatContext();
    refreshSessions();
  });
  $('chatStatusBtn').addEventListener('click', () => runSafeClaw(currentSessionArgs('status'), 'Session Status'));
  $('chatMemoryBtn').addEventListener('click', () => runSafeClaw(currentSessionArgs('memory'), 'Session Memory'));
  $('chatResetBtn').addEventListener('click', async () => {
    await runSafeClaw(currentSessionArgs('reset'), 'Reset Session');
    refreshSessions();
  });
  $('rememberBtn').addEventListener('click', () => {
    const note = $('memoryNote').value.trim() || lastMemoryTarget;
    if (!note) return;
    $('chatInput').value = `Remember this for this session: ${note}`;
    sendChat();
    $('memoryNote').value = '';
  });
  $('forgetLastBtn').addEventListener('click', () => runSafeClaw(currentSessionArgs('memory-forget', [lastMemoryTarget || 'last']), 'Forget Memory'));
  $('searchMemoryBtn').addEventListener('click', () => {
    const query = $('memoryNote').value.trim() || prompt('Search memory for');
    if (query) runSafeClaw(currentSessionArgs('memory-search', [query]), 'Search Memory');
  });
  $('exportSessionBtn').addEventListener('click', () => runSafeClaw(currentSessionArgs('export'), 'Export Session'));
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
    if (payload.type === 'exit') {
      setStatus(payload.code === 0 ? 'Done' : 'Failed', payload.code === 0 ? 'ok' : 'error');
      if (activeChatItem) setMessageState(activeChatItem, payload.code === 0 ? 'done' : 'failed');
      refreshSessions();
    }
    if (activeChatResponse && payload.type === 'stdout') {
      activeChatResponse.textContent += payload.text;
      detectApproval(payload.text);
      $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
    }
    if (activeChatResponse && ['stderr', 'error'].includes(payload.type)) {
      addResultBlock(activeChatResponse, payload.type === 'stderr' ? 'stderr' : 'error', payload.text);
      detectApproval(payload.text);
      $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
    }
    if (activeChatResponse && payload.type === 'exit') {
      activeChatResponse = null;
      activeChatItem = null;
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
  updateChatContext();
  renderAttachments();
  await refreshSessions();
}

init();
