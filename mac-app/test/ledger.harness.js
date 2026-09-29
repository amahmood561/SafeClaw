// Exercise the ledger against a minimal DOM stub: does it count what actually
// happened, and refuse to count what was only requested?
const fs = require('fs');
const src = fs.readFileSync('mac-app/src/renderer.js', 'utf8');
const start = src.indexOf('const CAPABILITY_TOOLS');
const code = src.slice(start);

const nodes = {};
function makeNode(id) {
  return {
    id, value: '', textContent: '', innerHTML: '', title: '', options: [],
    className: '', appendChild(c){ this.options.push(c); },
    addEventListener(){}, dispatchEvent(){},
  };
}
for (const id of ['ledgerList','ledgerProfile','ledgerWorkspace','ledgerResetBtn','chatPermission','permissionProfile','workspace']) {
  nodes[id] = makeNode(id);
}
global.$ = (id) => nodes[id];
global.escapeHtml = (s) => String(s);
global.document = { createElement: () => makeNode('el') };

const rows = [];
nodes.ledgerList.appendChild = (c) => rows.push(c);
Object.defineProperty(nodes.ledgerList, 'innerHTML', { set(){ rows.length = 0; }, get(){ return ''; } });

eval(code);

function show(label) {
  console.log(`\n${label}`);
  for (const r of rows) {
    const text = r.innerHTML.replace(/<[^>]+>/g, '|').split('|').filter(x => x.trim());
    console.log(`  [${r.className.replace('ledger-row ','')}] ${text.join(' ')}`);
  }
}

nodes.chatPermission.value = 'readonly';
nodes.workspace.value = '/Users/me/Documents';
renderLedger();
show('readonly, nothing done yet:');

recordLedger({type:'tool_message', tool:'read_file'});
recordLedger({type:'tool_message', tool:'list_files'});
recordLedger({type:'tool_call', tool:'write_file'});      // requested only
recordLedger({type:'approval_required', tool:'write_file'});
show('read twice, one write awaiting approval:');

recordLedger({type:'approval_denied', tool:'write_file'});
show('after the user refused the write:');

console.log('\nworkspace shown:', nodes.ledgerWorkspace.textContent);
