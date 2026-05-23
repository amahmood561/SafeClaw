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
const providerPresets = {
  openai: {
    label: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4.1-mini',
    hint: 'Best tested path for SafeClaw tool calling and streaming.',
  },
  ollama: {
    label: 'Ollama',
    baseUrl: 'http://localhost:11434/v1',
    model: 'llama3.1',
    hint: 'Local OpenAI-compatible endpoint. Use API key "ollama".',
  },
  groq: {
    label: 'Groq',
    baseUrl: 'https://api.groq.com/openai/v1',
    model: 'openai/gpt-oss-20b',
    hint: 'Fast OpenAI-compatible endpoint. Save your Groq key as OPENAI_API_KEY.',
  },
  openrouter: {
    label: 'OpenRouter / Claude',
    baseUrl: 'https://openrouter.ai/api/v1',
    model: 'anthropic/claude-3.5-sonnet',
    hint: 'Recommended route for Claude. Save your OpenRouter key as OPENAI_API_KEY.',
  },
  litellm: {
    label: 'LiteLLM gateway',
    baseUrl: 'http://localhost:4000/v1',
    model: 'anthropic/claude-3-5-sonnet-latest',
    hint: 'Use this when running your own OpenAI-compatible LiteLLM proxy.',
  },
  custom: {
    label: 'Custom OpenAI-compatible',
    baseUrl: '',
    model: '',
    hint: 'Use any provider that supports /chat/completions.',
  },
};
const textAttachmentLimit = 120000;
const textPreviewLimit = 40000;
const hugeFileLimit = 2 * 1024 * 1024;
const viewTitles = {
  setup: 'Setup',
  run: 'Run SafeClaw',
  chat: 'Chat',
  jarvis: 'Jarvis Mode',
  whatsapp: 'Phone',
  database: 'Databases',
  logs: 'Output',
};

let activeChatResponse = null;
let activeChatItem = null;
let activeChatHadEvents = false;
let lastChatPrompt = '';
let chatAttachments = [];
let lastMemoryTarget = '';
let eventLineBuffer = '';
let saveConfigAfterInstall = false;
let providerErrorActive = false;
let jarvisEnabled = false;
let jarvisQueue = [];
let jarvisApprovals = [];
let activeTaskResult = false;
let activeTaskResultId = '';
let activeTaskHadEvents = false;
let taskProviderErrorActive = false;
let loadingSession = false;
let activeTaskText = '';
const responseText = new WeakMap();
let toolActivityCount = 0;

function setOptions(select, values) {
  select.innerHTML = values.map((value) => `<option value="${value}">${value}</option>`).join('');
}

function settings() {
  return {
    installDir: $('installDir').value.trim(),
    repoUrl: $('repoUrl').value.trim(),
    ref: $('ref').value.trim(),
    providerPreset: $('providerPreset').value,
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
    twilioSid: $('twilioSid').value.trim(),
    twilioToken: $('twilioToken').value,
    twilioFrom: $('twilioFrom').value.trim(),
    allowedSenders: $('allowedSenders').value.trim(),
    telegramToken: $('telegramToken').value,
    allowedTelegramUsers: $('allowedTelegramUsers').value.trim(),
  };
}

function inferProviderPreset(baseUrl) {
  const normalized = (baseUrl || '').replace(/\/$/, '');
  for (const [id, preset] of Object.entries(providerPresets)) {
    if (preset.baseUrl && preset.baseUrl.replace(/\/$/, '') === normalized) return id;
  }
  return 'custom';
}

function updateProviderHint() {
  const preset = providerPresets[$('providerPreset').value] || providerPresets.custom;
  $('providerHint').innerHTML = `${escapeHtml(preset.hint)} Click <strong>Save Config</strong> after changing credentials.`;
}

function applyProviderPreset() {
  const preset = providerPresets[$('providerPreset').value] || providerPresets.custom;
  if (preset.baseUrl) $('baseUrl').value = preset.baseUrl;
  if (preset.model) $('model').value = preset.model;
  if ($('providerPreset').value === 'ollama' && !$('apiKey').value) $('apiKey').value = 'ollama';
  updateProviderHint();
  updateChatContext();
  updateJarvisContext();
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
  const provider = providerPresets[$('providerPreset').value]?.label || 'Custom provider';
  const profile = $('chatPermission').value || $('permissionProfile').value || 'readonly';
  const approval = $('approvalMode').value || 'ask';
  $('chatContextBar').innerHTML = [
    ['Workspace', workspaceDisplay()],
    ['Provider', provider],
    ['Permission', profile],
    ['Approval', approval],
    ['Model', model],
  ].map(([label, value]) => `<span><strong>${label}</strong>${value}</span>`).join('');
}

function isJarvisEnabled() {
  return window.localStorage.getItem('safeclaw.jarvis.enabled') === 'true';
}

function setJarvisEnabled(enabled) {
  jarvisEnabled = Boolean(enabled);
  window.localStorage.setItem('safeclaw.jarvis.enabled', jarvisEnabled ? 'true' : 'false');
  if ($('jarvisModeToggle')) $('jarvisModeToggle').checked = jarvisEnabled;
  if ($('setupJarvisToggle')) $('setupJarvisToggle').checked = jarvisEnabled;
  const jarvisNav = document.querySelector('[data-view="jarvis"]');
  if (jarvisNav) {
    jarvisNav.classList.toggle('disabled', !jarvisEnabled);
    jarvisNav.setAttribute('aria-disabled', jarvisEnabled ? 'false' : 'true');
  }
  document.body.classList.toggle('jarvis-enabled', jarvisEnabled);
  if (!jarvisEnabled && document.querySelector('#jarvis.view.active')) {
    showView('chat');
  }
  updateJarvisContext();
}

function updateJarvisContext() {
  if (!$('jarvisContext')) return;
  const model = $('chatModel').value.trim() || $('model').value.trim() || 'default model';
  const provider = providerPresets[$('providerPreset').value]?.label || 'Custom provider';
  const profile = $('chatPermission').value || $('permissionProfile').value || 'readonly';
  const approval = $('approvalMode').value || 'ask';
  const workspace = workspaceDisplay();
  const state = jarvisEnabled ? 'Enabled' : 'Disabled';
  $('jarvisState').textContent = state;
  $('jarvisHeartbeat').textContent = jarvisEnabled ? 'Local app online' : 'Switch on Jarvis mode to use this view';
  $('jarvisWorkspace').textContent = workspace;
  $('jarvisModel').textContent = model;
  $('jarvisPermission').textContent = profile;
  $('jarvisApproval').textContent = approval;
  $('jarvisWhatsappPort').textContent = $('whatsappPort').value.trim() || '8080';
  $('jarvisContext').innerHTML = [
    ['Mode', state],
    ['Workspace', workspace],
    ['Provider', provider],
    ['Permission', profile],
    ['Approval', approval],
    ['Model', model],
  ].map(([label, value]) => `<span><strong>${label}</strong>${value}</span>`).join('');
}

function showView(name) {
  if (name === 'jarvis' && !jarvisEnabled) {
    setStatus('Jarvis disabled', 'idle');
    name = 'chat';
  }
  document.querySelectorAll('.view').forEach((view) => view.classList.toggle('active', view.id === name));
  document.querySelectorAll('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.view === name));
  $('viewTitle').textContent = viewTitles[name] || 'SafeClaw';
  if (name === 'chat') updateChatContext();
  if (name === 'jarvis') updateJarvisContext();
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
  $('providerPreset').value = env.SAFECLAW_PROVIDER_PRESET || inferProviderPreset($('baseUrl').value);
  updateProviderHint();
  if (env.WORKSPACE) $('workspace').value = env.WORKSPACE;
  if (env.SAFECLAW_PERMISSION_PROFILE) $('permissionProfile').value = env.SAFECLAW_PERMISSION_PROFILE;
  if (env.SAFECLAW_APPROVAL_MODE) $('approvalMode').value = env.SAFECLAW_APPROVAL_MODE;
  if (env.SAFECLAW_SQLITE_DATABASES) $('sqliteDatabases').value = env.SAFECLAW_SQLITE_DATABASES;
  if (env.TWILIO_ACCOUNT_SID) $('twilioSid').value = env.TWILIO_ACCOUNT_SID;
  if (env.TWILIO_AUTH_TOKEN) $('twilioToken').value = env.TWILIO_AUTH_TOKEN;
  if (env.TWILIO_WHATSAPP_FROM) $('twilioFrom').value = env.TWILIO_WHATSAPP_FROM;
  if (env.SAFECLAW_ALLOWED_SENDERS) $('allowedSenders').value = env.SAFECLAW_ALLOWED_SENDERS;
  if (env.TELEGRAM_BOT_TOKEN) $('telegramToken').value = env.TELEGRAM_BOT_TOKEN;
  if (env.SAFECLAW_ALLOWED_TELEGRAM_USERS) $('allowedTelegramUsers').value = env.SAFECLAW_ALLOWED_TELEGRAM_USERS;
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

function setTaskResultState(text, mode = 'idle') {
  const state = $('taskResultState');
  if (!state) return;
  state.textContent = text;
  state.dataset.mode = mode;
}

function clearTaskResult() {
  $('taskResult').hidden = false;
  activeTaskText = '';
  renderTaskResultText();
  setTaskResultState('Running', 'running');
}

function fixMojibake(text) {
  return String(text || '')
    .replaceAll('â', '-')
    .replaceAll('â', '-')
    .replaceAll('â', '-')
    .replaceAll('â', "'")
    .replaceAll('â', "'")
    .replaceAll('â', '"')
    .replaceAll('â', '"')
    .replaceAll('â¢', '-')
    .replaceAll('Â ', ' ')
    .replaceAll('Â', '');
}

function escapeHtml(text) {
  return String(text || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function inlineMarkdown(text) {
  return escapeHtml(fixMojibake(text))
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2">$1</a>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}

function tableHtml(lines) {
  const rows = lines
    .filter((line) => !/^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line))
    .map((line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => inlineMarkdown(cell.trim())));
  if (!rows.length) return '';
  const [head, ...body] = rows;
  return `<div class="markdown-table-wrap"><table class="markdown-table"><thead><tr>${head.map((cell) => `<th>${cell}</th>`).join('')}</tr></thead><tbody>${body.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function renderMarkdownLite(text) {
  const lines = fixMojibake(text).split(/\r?\n/);
  const html = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) continue;
    if (/^```/.test(line.trim())) {
      const code = [];
      index += 1;
      while (index < lines.length && !/^```/.test(lines[index].trim())) {
        code.push(lines[index]);
        index += 1;
      }
      html.push(`<pre class="markdown-code"><code>${escapeHtml(fixMojibake(code.join('\n')))}</code></pre>`);
      continue;
    }
    if (/^\s*-{3,}\s*$/.test(line)) {
      html.push('<hr>');
      continue;
    }
    if (/^\s*\|.+\|\s*$/.test(line)) {
      const tableLines = [];
      while (index < lines.length && /^\s*\|.+\|\s*$/.test(lines[index])) {
        tableLines.push(lines[index]);
        index += 1;
      }
      index -= 1;
      html.push(tableHtml(tableLines));
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 1, 4);
      html.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(`<li>${inlineMarkdown(lines[index].replace(/^\s*[-*]\s+/, ''))}</li>`);
        index += 1;
      }
      index -= 1;
      html.push(`<ul>${items.join('')}</ul>`);
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        items.push(`<li>${inlineMarkdown(lines[index].replace(/^\s*\d+\.\s+/, ''))}</li>`);
        index += 1;
      }
      index -= 1;
      html.push(`<ol>${items.join('')}</ol>`);
      continue;
    }
    html.push(`<p>${inlineMarkdown(line)}</p>`);
  }
  return html.join('');
}

function setResponseText(node, text) {
  const clean = fixMojibake(text);
  responseText.set(node, clean);
  node.classList.add('rendered-response');
  node.innerHTML = clean.trim() ? renderMarkdownLite(clean) : '';
  node.scrollTop = node.scrollHeight;
}

function appendResponseText(node, text) {
  const next = `${responseText.get(node) || ''}${text || ''}`;
  setResponseText(node, next);
}

function getResponseText(node) {
  return responseText.get(node) || node.textContent || '';
}

function renderTaskResultText() {
  const body = $('taskResultBody');
  if (activeTaskText.trim()) {
    setResponseText(body, activeTaskText);
  } else {
    responseText.set(body, '');
    body.innerHTML = '<div class="result-placeholder">Waiting for SafeClaw...</div>';
  }
  body.scrollTop = body.scrollHeight;
}

function isActiveTaskPayload(payload) {
  return activeTaskResult && payload.id === activeTaskResultId && !activeChatResponse;
}

function appendTaskResult(text) {
  activeTaskText += text;
  renderTaskResultText();
}

function renderTaskProviderError(event) {
  taskProviderErrorActive = true;
  const fix = event.code === 'insufficient_quota' || event.error_type === 'insufficient_quota'
    ? '\n\nFix: check OpenAI API billing/quota at https://platform.openai.com/settings/organization/billing/overview'
    : '';
  activeTaskText = `Provider error: ${event.message || 'The model provider rejected the request.'}${fix}`;
  renderTaskResultText();
  setTaskResultState('Failed', 'error');
  setStatus('Provider error', 'error');
}

function handleTaskEvent(event) {
  if (!event || !event.type) return;
  if (event.type === 'task_started') {
    setTaskResultState('Running', 'running');
    setStatus('Running', 'running');
  }
  if (event.type === 'assistant_delta') {
    appendTaskResult(event.content || '');
  }
  if (event.type === 'assistant_message' && !activeTaskText.trim()) {
    activeTaskText = event.content || '';
    renderTaskResultText();
  }
  if (event.type === 'provider_error') {
    renderTaskProviderError(event);
  }
  if (event.type === 'tool_error') {
    appendTaskResult(`\n\nTool error: ${event.content || event.tool || 'Unknown tool error'}`);
  }
  if (event.type === 'approval_required') {
    renderApprovalCard(event.tool || 'Action approval', event.subject || event.arguments_preview || '', event);
    appendTaskResult('\n\nWaiting for approval in the approval card.');
    setTaskResultState('Needs approval', 'running');
  }
  if (event.type === 'task_done') {
    if (!activeTaskText.trim()) {
      activeTaskText = event.content || '';
      renderTaskResultText();
    }
    setTaskResultState('Done', 'ok');
    setStatus('Done', 'ok');
  }
}

async function runTaskInPanel() {
  const task = $('taskInput').value.trim();
  if (!task) return;
  showView('run');
  clearTaskResult();
  activeTaskResult = true;
  activeTaskResultId = 'run';
  activeTaskHadEvents = false;
  taskProviderErrorActive = false;
  const args = ['run', task, '--events'];
  const permission = $('permissionProfile').value;
  if (permission) args.push('--permission-profile', permission);
  const result = await window.safeclaw.command(settings(), args, 'Run Task');
  if (!result.ok) {
    appendTaskResult(`Error: ${result.error}`);
    setTaskResultState('Failed', 'error');
    activeTaskResult = false;
    activeTaskResultId = '';
  }
}

async function showToolsInPanel() {
  showView('run');
  clearTaskResult();
  activeTaskResult = true;
  activeTaskResultId = 'tools';
  activeTaskHadEvents = false;
  taskProviderErrorActive = false;
  const result = await window.safeclaw.command(settings(), ['tools'], 'Show Tools');
  if (!result.ok) {
    appendTaskResult(`Error: ${result.error}`);
    setTaskResultState('Failed', 'error');
    activeTaskResult = false;
    activeTaskResultId = '';
  }
}

function chatArgs(command, extra = []) {
  const session = chatSessionId();
  const model = $('chatModel').value.trim();
  const permission = $('chatPermission').value;
  const args = [command, ...extra, '--session', session];
  if (command === 'run') args.push('--events');
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
  if (role === 'assistant') {
    setResponseText(body, text);
  } else {
    body.textContent = fixMojibake(text);
  }
  item.append(label, body);
  $('chatMessages').appendChild(item);
  $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
  return { item, body };
}

function sessionUserText(content = '') {
  const text = String(content || '');
  const match = text.match(/(?:^|\n)User task:\n([\s\S]*)$/);
  return (match ? match[1] : text).trim();
}

function renderSessionMessages(session) {
  const messages = Array.isArray(session?.messages) ? session.messages : [];
  $('chatMessages').innerHTML = '';
  toolActivityCount = 0;
  $('toolActivityCount').textContent = '0';
  $('toolActivityList').innerHTML = '';

  const visibleMessages = messages
    .filter((message) => ['user', 'assistant'].includes(message.role))
    .map((message) => ({
      role: message.role === 'assistant' ? 'assistant' : 'user',
      content: message.role === 'user' ? sessionUserText(message.content) : String(message.content || '').trim(),
    }))
    .filter((message) => message.content);

  if (!visibleMessages.length) {
    resetEmptyChat();
    return;
  }

  for (const message of visibleMessages) {
    addChatMessage(message.role, message.content, 'done');
  }
}

async function loadChatSession(sessionId = chatSessionId()) {
  loadingSession = true;
  const result = await window.safeclaw.loadSession(settings(), sessionId).catch((error) => ({ ok: false, error: error.message }));
  loadingSession = false;
  if (!result.ok) {
    appendOutput(`Load session failed: ${result.error}\n`);
    return;
  }
  renderSessionMessages(result.session);
}

function addResultBlock(parent, type, text) {
  const block = document.createElement('pre');
  block.className = `result-block ${type}`;
  block.textContent = text;
  parent.appendChild(block);
  $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
  return block;
}

function addToolActivity(event) {
  const list = $('toolActivityList');
  if (!list) return;
  toolActivityCount += 1;
  $('toolActivityCount').textContent = String(toolActivityCount);
  const row = document.createElement('div');
  row.className = `tool-activity-item ${event.type}`;
  const title = event.tool || event.type.replaceAll('_', ' ');
  const detail = event.subject || event.arguments_preview || event.content || event.reason || '';
  row.innerHTML = `
    <strong>${escapeHtml(title)}</strong>
    <span>${escapeHtml(event.type.replaceAll('_', ' '))}</span>
    ${detail ? `<code>${escapeHtml(String(detail).slice(0, 600))}</code>` : ''}
  `;
  list.prepend(row);
}

function splitEventLines(text) {
  const combined = eventLineBuffer + text;
  const lines = combined.split(/\r?\n/);
  eventLineBuffer = lines.pop() || '';
  const events = [];
  const visible = [];
  for (const line of lines) {
    if (line.startsWith('SAFECLAW_EVENT ')) {
      try {
        events.push(JSON.parse(line.slice('SAFECLAW_EVENT '.length)));
      } catch (_error) {
        visible.push(line);
      }
    } else {
      visible.push(line);
    }
  }
  return { events, visibleText: visible.length ? `${visible.join('\n')}\n` : '' };
}

function handleStructuredEvent(event) {
  if (!event || !event.type) return;
  if (event.type === 'task_started') {
    setStatus('Running', 'running');
    if (activeChatItem) setMessageState(activeChatItem, 'running');
  }
  if (event.type === 'assistant_delta' && activeChatResponse) {
    appendResponseText(activeChatResponse, event.content || '');
    $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
  }
  if (event.type === 'assistant_message' && activeChatResponse && !getResponseText(activeChatResponse).trim()) {
    setResponseText(activeChatResponse, event.content || '');
  }
  if (['tool_call', 'tool_started', 'tool_result', 'tool_message', 'tool_blocked'].includes(event.type)) {
    addToolActivity(event);
    return;
  }
  if (event.type === 'tool_error' && activeChatResponse) {
    addToolActivity(event);
    addResultBlock(activeChatResponse, 'error', event.content || `Tool error: ${event.tool}`);
  }
  if (event.type === 'provider_error' && activeChatResponse) {
    renderProviderError(event);
  }
  if (event.type === 'approval_required') {
    addToolActivity(event);
    renderApprovalCard(event.tool || 'Action approval', event.subject || event.arguments_preview || '', event);
  }
  if (event.type === 'approval_decision' && activeChatItem) {
    setMessageState(activeChatItem, event.decision === 'allowed' ? 'running' : 'stopped');
  }
  if (event.type === 'task_done') {
    if (activeChatResponse && !getResponseText(activeChatResponse).trim() && event.content) {
      setResponseText(activeChatResponse, event.content);
    }
    setStatus('Done', 'ok');
    if (activeChatItem) setMessageState(activeChatItem, 'done');
  }
}

function renderProviderError(event) {
  if (!activeChatResponse) return;
  providerErrorActive = true;
  const fix = event.code === 'insufficient_quota' || event.error_type === 'insufficient_quota'
    ? '\n\nFix: check OpenAI API billing/quota at https://platform.openai.com/settings/organization/billing/overview'
    : '';
  setResponseText(activeChatResponse, `Provider error: ${event.message || 'The model provider rejected the request.'}${fix}`);
  if (activeChatItem) setMessageState(activeChatItem, 'failed');
  setStatus('Provider error', 'error');
}

function extractLegacyProviderError(text) {
  const marker = 'Error:';
  const index = text.indexOf(marker);
  if (index === -1) return null;
  const raw = text.slice(index + marker.length).trim();
  if (!raw.startsWith('{')) return { message: raw };
  try {
    const payload = JSON.parse(raw);
    const error = payload.error || {};
    return {
      type: 'provider_error',
      message: error.message || raw,
      error_type: error.type || null,
      code: error.code || null,
      status_code: null,
    };
  } catch (_error) {
    return { type: 'provider_error', message: raw };
  }
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
  let current = chatSessionId();
  list.innerHTML = '';
  const sessions = await window.safeclaw.sessions(settings()).catch(() => [{ id: 'desktop', updatedAt: '' }]);
  if (!sessions.some((session) => session.id === current)) {
    current = sessions[0]?.id || 'desktop';
    $('chatSession').value = current;
    updateChatContext();
    updateJarvisContext();
    await loadChatSession(current);
  }
  for (const session of sessions) {
    const item = document.createElement('button');
    item.className = 'session-item';
    item.type = 'button';
    item.classList.toggle('active', session.id === current);
    item.innerHTML = `<strong>${session.id}</strong><span>${formatTime(session.updatedAt)} · ${session.messages || 0} messages</span>`;
    item.addEventListener('click', async () => {
      $('chatSession').value = session.id;
      updateChatContext();
      updateJarvisContext();
      await loadChatSession(session.id);
      await refreshSessions();
    });
    list.appendChild(item);
  }
}

function currentSessionArgs(command, extra = []) {
  return [command, ...extra, '--session', chatSessionId()];
}

function renderApprovalCard(kind, detail, event = {}) {
  const tray = $('approvalTray');
  tray.hidden = false;
  tray.innerHTML = '';
  const card = document.createElement('div');
  card.className = 'approval-card';
  card.innerHTML = `
    <span class="tag">Needs approval</span>
    <h3>${kind}</h3>
    <p>${event.reason || 'SafeClaw needs approval before continuing.'}</p>
    <pre>${[
      event.subject ? `Subject: ${event.subject}` : detail,
      event.profile ? `Profile: ${event.profile}` : '',
      event.arguments_preview ? `Args: ${event.arguments_preview}` : '',
    ].filter(Boolean).join('\n')}</pre>
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
  addJarvisApproval(kind, detail, event);
  if (activeChatItem) setMessageState(activeChatItem, 'needs approval');
  setStatus('Needs approval', 'running');
}

function renderJarvisQueue() {
  const list = $('jarvisQueue');
  if (!list) return;
  list.innerHTML = '';
  if (!jarvisQueue.length) {
    list.innerHTML = '<div class="jarvis-empty">No queued tasks.</div>';
    return;
  }
  jarvisQueue.forEach((task, index) => {
    const row = document.createElement('div');
    row.className = 'jarvis-list-item';
    row.innerHTML = `<strong>${index + 1}. ${task.text}</strong><span>${formatTime(task.createdAt)}</span>`;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => {
      jarvisQueue = jarvisQueue.filter((item) => item.id !== task.id);
      renderJarvisQueue();
    });
    row.appendChild(remove);
    list.appendChild(row);
  });
}

function addJarvisQueueTask(text) {
  const task = text.trim();
  if (!task) return;
  jarvisQueue.push({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    text: task,
    createdAt: new Date().toISOString(),
  });
  $('jarvisInput').value = '';
  renderJarvisQueue();
  setStatus('Queued', 'ok');
}

function runJarvisTask(text) {
  const task = text.trim();
  if (!task) return;
  $('chatInput').value = task;
  showView('chat');
  sendChat();
}

function renderJarvisApprovals() {
  const list = $('jarvisApprovals');
  if (!list) return;
  list.innerHTML = '';
  if (!jarvisApprovals.length) {
    list.innerHTML = '<div class="jarvis-empty">No approvals waiting.</div>';
    return;
  }
  jarvisApprovals.slice(-5).reverse().forEach((approval) => {
    const row = document.createElement('div');
    row.className = 'jarvis-list-item approval';
    row.innerHTML = `
      <strong>${approval.kind}</strong>
      <span>${approval.reason}</span>
      <code>${approval.detail}</code>
    `;
    list.appendChild(row);
  });
}

function addJarvisApproval(kind, detail, event = {}) {
  jarvisApprovals.push({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    kind,
    detail: (event.subject || detail || event.arguments_preview || '').toString().slice(0, 240),
    reason: event.reason || 'SafeClaw is waiting for a permission decision.',
  });
  renderJarvisApprovals();
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
  toolActivityCount = 0;
  $('toolActivityCount').textContent = '0';
  $('toolActivityList').innerHTML = '';
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
  activeChatHadEvents = false;
  providerErrorActive = false;
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
    saveConfigAfterInstall = true;
    const result = await window.safeclaw.install(settings());
    if (!result.ok) {
      saveConfigAfterInstall = false;
      appendOutput(`Error: ${result.error}\n`);
    }
  });

  $('saveConfigBtn').addEventListener('click', saveEnv);
  $('loadConfigBtn').addEventListener('click', loadEnv);
  $('doctorBtn').addEventListener('click', () => runSafeClaw(['doctor'], 'Run Doctor'));
  $('providerPreset').addEventListener('change', applyProviderPreset);
  $('providerTestBtn').addEventListener('click', () => runSafeClaw(['provider-test'], 'Provider Test'));
  $('openFolderBtn').addEventListener('click', () => window.safeclaw.openPath(settings().installDir));
  $('runTaskBtn').addEventListener('click', runTaskInPanel);
  $('toolsBtn').addEventListener('click', showToolsInPanel);
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
    updateJarvisContext();
    await refreshSessions();
    await loadChatSession(newId);
  });
  $('deleteSessionBtn').addEventListener('click', async () => {
    const session = chatSessionId();
    if (!confirm(`Delete session "${session}"?`)) return;
    const result = await window.safeclaw.deleteSession(settings(), session);
    if (!result.ok) return appendOutput(`Delete failed: ${result.error}\n`);
    $('chatSession').value = 'desktop';
    updateChatContext();
    updateJarvisContext();
    await refreshSessions();
    await loadChatSession('desktop');
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
  ['workspace', 'model', 'chatModel', 'chatPermission', 'permissionProfile', 'approvalMode', 'whatsappPort'].forEach((id) => {
    $(id).addEventListener('input', updateChatContext);
    $(id).addEventListener('change', updateChatContext);
    $(id).addEventListener('input', updateJarvisContext);
    $(id).addEventListener('change', updateJarvisContext);
  });
  $('chatSession').addEventListener('input', () => {
    updateChatContext();
    updateJarvisContext();
    if (!loadingSession) refreshSessions();
  });
  $('chatStatusBtn').addEventListener('click', () => runSafeClaw(currentSessionArgs('status'), 'Session Status'));
  $('chatMemoryBtn').addEventListener('click', () => runSafeClaw(currentSessionArgs('memory'), 'Session Memory'));
  $('chatResetBtn').addEventListener('click', async () => {
    await runSafeClaw(currentSessionArgs('reset'), 'Reset Session');
    await refreshSessions();
    await loadChatSession(chatSessionId());
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
  $('jarvisModeToggle').addEventListener('change', (event) => setJarvisEnabled(event.target.checked));
  $('setupJarvisToggle').addEventListener('change', (event) => setJarvisEnabled(event.target.checked));
  $('jarvisRunBtn').addEventListener('click', () => runJarvisTask($('jarvisInput').value));
  $('jarvisQueueBtn').addEventListener('click', () => addJarvisQueueTask($('jarvisInput').value));
  $('jarvisRunNextBtn').addEventListener('click', () => {
    const next = jarvisQueue.shift();
    renderJarvisQueue();
    if (next) runJarvisTask(next.text);
  });
  $('jarvisClearQueueBtn').addEventListener('click', () => {
    jarvisQueue = [];
    renderJarvisQueue();
  });
  $('jarvisStopBtn').addEventListener('click', () => $('stopChatBtn').click());
  $('jarvisOpenChatBtn').addEventListener('click', () => showView('chat'));
  $('jarvisPushToTalkBtn').addEventListener('click', () => {
    setStatus('Voice not ready', 'idle');
    appendOutput('Jarvis voice capture is not implemented yet. Type a command or queue a task for now.\n');
  });
  $('jarvisServiceStatusBtn').addEventListener('click', () => {
    $('jarvisServiceState').textContent = 'Checking...';
    runSafeClaw(['service-status'], 'Service Status');
  });
  $('jarvisStartServiceBtn').addEventListener('click', () => {
    $('jarvisServiceState').textContent = 'Starting...';
    runSafeClaw(['service-start'], 'Start Service');
  });
  $('jarvisWhatsappSetupBtn').addEventListener('click', () => runSafeClaw(['whatsapp-setup'], 'WhatsApp Setup'));
  $('openRepo').addEventListener('click', () => window.safeclaw.openUrl('https://github.com/amahmood561/SafeClaw'));
  $('twilioBtn').addEventListener('click', () => window.safeclaw.openUrl('https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn'));
  $('botFatherBtn').addEventListener('click', () => window.safeclaw.openUrl('https://t.me/BotFather'));
  $('saveTelegramConfigBtn').addEventListener('click', saveEnv);
  $('startTelegramBtn').addEventListener('click', () => runSafeClaw(['telegram'], 'Start Telegram Bot'));
  $('telegramSetupBtn').addEventListener('click', () => runSafeClaw(['telegram-setup'], 'Telegram Setup'));
  $('saveWhatsappConfigBtn').addEventListener('click', saveEnv);
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
    const parsed = splitEventLines(payload.text || '');
    parsed.events.forEach((event) => {
      if (isActiveTaskPayload(payload)) {
        activeTaskHadEvents = true;
        handleTaskEvent(event);
      } else {
        activeChatHadEvents = true;
        handleStructuredEvent(event);
      }
    });
    const visibleText = parsed.visibleText;
    if (payload.type === 'start') setStatus('Running', 'running');
    if (payload.type === 'exit') {
      if (eventLineBuffer.startsWith('SAFECLAW_EVENT ')) {
        try {
          activeChatHadEvents = true;
          handleStructuredEvent(JSON.parse(eventLineBuffer.slice('SAFECLAW_EVENT '.length)));
        } catch (_error) {
          appendOutput(`${eventLineBuffer}\n`);
        }
      }
      eventLineBuffer = '';
      if (!providerErrorActive && !taskProviderErrorActive) {
        setStatus(payload.code === 0 ? 'Done' : 'Failed', payload.code === 0 ? 'ok' : 'error');
        if (activeChatItem) setMessageState(activeChatItem, payload.code === 0 ? 'done' : 'failed');
        if (isActiveTaskPayload(payload) && !taskProviderErrorActive) {
          setTaskResultState(payload.code === 0 ? 'Done' : 'Failed', payload.code === 0 ? 'ok' : 'error');
        }
      }
      refreshSessions();
      if (payload.id === 'install' && saveConfigAfterInstall) {
        saveConfigAfterInstall = false;
        if (payload.code === 0) {
          saveEnv().then(loadEnv).catch((error) => appendOutput(`Config save failed: ${error.message}\n`));
        } else {
          appendOutput('Install failed, so config was not saved.\n');
        }
      }
    }
    if (activeChatResponse && payload.type === 'stdout' && visibleText && !activeChatHadEvents) {
      const providerError = extractLegacyProviderError(visibleText);
      if (providerError) {
        renderProviderError(providerError);
      } else {
        appendResponseText(activeChatResponse, visibleText);
        detectApproval(visibleText);
      }
      $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
    }
    if (activeChatResponse && ['stderr', 'error'].includes(payload.type) && visibleText) {
      const providerError = extractLegacyProviderError(visibleText);
      if (providerError) {
        renderProviderError(providerError);
      } else {
        addResultBlock(activeChatResponse, payload.type === 'stderr' ? 'stderr' : 'error', visibleText);
        detectApproval(visibleText);
      }
      $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
    }
    if (activeChatResponse && payload.type === 'exit') {
      activeChatResponse = null;
      activeChatItem = null;
      activeChatHadEvents = false;
      providerErrorActive = false;
    }
    if (isActiveTaskPayload(payload) && payload.type === 'stdout' && visibleText && !activeTaskHadEvents) {
      appendTaskResult(visibleText);
    }
    if (isActiveTaskPayload(payload) && ['stderr', 'error'].includes(payload.type) && visibleText && !activeTaskHadEvents) {
      const providerError = extractLegacyProviderError(visibleText);
      if (providerError) {
        renderTaskProviderError(providerError);
      } else {
        appendTaskResult(visibleText);
      }
    }
    if (isActiveTaskPayload(payload) && payload.type === 'exit') {
      activeTaskResult = false;
      activeTaskResultId = '';
      activeTaskHadEvents = false;
      taskProviderErrorActive = false;
    }
    if (visibleText || payload.type === 'start' || payload.type === 'exit') {
      appendOutput(visibleText || payload.text);
    }
  });
}

async function init() {
  setOptions($('permissionProfile'), permissionProfiles);
  setOptions($('chatPermission'), permissionProfiles);
  setOptions($('approvalMode'), approvalModes);
  setOptions($('providerPreset'), Object.entries(providerPresets).map(([id, preset]) => `${id}:${preset.label}`));
  $('providerPreset').innerHTML = Object.entries(providerPresets)
    .map(([id, preset]) => `<option value="${id}">${preset.label}</option>`)
    .join('');
  await loadDefaults();
  await loadEnv().catch(() => {});
  bindEvents();
  setJarvisEnabled(isJarvisEnabled());
  updateChatContext();
  updateJarvisContext();
  renderJarvisQueue();
  renderJarvisApprovals();
  renderAttachments();
  await refreshSessions();
  await loadChatSession(chatSessionId());
}

init();
