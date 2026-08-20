/* ═══════════════════════════════════════════════════════
   Virtual Contact Manager — PWA
   ═══════════════════════════════════════════════════════ */

// ── Service Worker Registration ──
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}

// ═══════════════════════════════════════════════════════
// DATABASE (IndexedDB)
// ═══════════════════════════════════════════════════════
const DB_NAME = 'VCM_DB';
const DB_VER = 1;
let db = null;

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    req.onupgradeneeded = e => {
      const d = e.target.result;
      if (!d.objectStoreNames.contains('contacts')) {
        const store = d.createObjectStore('contacts', { keyPath: 'internal_id' });
        store.createIndex('phone', 'phone', { unique: false });
        store.createIndex('created_by_app', 'created_by_app', { unique: false });
        store.createIndex('status', 'status', { unique: false });
      }
    };
    req.onsuccess = e => { db = e.target.result; resolve(db); };
    req.onerror = e => reject(e.target.error);
  });
}

function dbPut(store, data) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    const s = tx.objectStore(store);
    if (Array.isArray(data)) data.forEach(d => s.put(d));
    else s.put(data);
    tx.oncomplete = () => resolve();
    tx.onerror = e => reject(e.target.error);
  });
}

function dbGetAll(store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readonly');
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = e => reject(e.target.error);
  });
}

function dbDelete(store, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    tx.objectStore(store).delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = e => reject(e.target.error);
  });
}

function dbClear(store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    tx.objectStore(store).clear();
    tx.oncomplete = () => resolve();
    tx.onerror = e => reject(e.target.error);
  });
}

function dbCount(store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readonly');
    const req = tx.objectStore(store).count();
    req.onsuccess = () => resolve(req.result);
    req.onerror = e => reject(e.target.error);
  });
}

// ═══════════════════════════════════════════════════════
// PHONE UTILITIES
// ═══════════════════════════════════════════════════════
function normalizePhone(raw) {
  if (!raw) return null;
  let digits = raw.replace(/[^\d]/g, '');
  if (!digits) return null;

  // Strip leading 00
  while (digits.length > 2 && digits.startsWith('00')) {
    digits = digits.slice(2);
  }

  // Iranian numbers
  if (digits.startsWith('0') && digits.length === 11) {
    digits = '98' + digits.slice(1);
  } else if (digits.startsWith('98') && digits.length === 12) {
    // already good
  } else if (digits.length === 10 && digits.startsWith('9')) {
    digits = '98' + digits;
  } else {
    if (digits.length < 7 || digits.length > 15) return null;
  }

  return '+' + digits;
}

function formatDisplay(phone) {
  if (phone.startsWith('+98') && phone.length === 13) {
    const local = phone.slice(3);
    return `+98 ${local.slice(0,3)} ${local.slice(3,6)} ${local.slice(6)}`;
  }
  return phone;
}

function generateNumbers(start, count, step) {
  const norm = normalizePhone(start);
  if (!norm) throw new Error('Invalid start number');
  const base = BigInt(norm.slice(1)); // remove '+'
  const results = [];
  for (let i = 0; i < count; i++) {
    const num = base + BigInt(i * step);
    if (num.toString().length > 15) break;
    results.push('+' + num.toString());
  }
  return results;
}

// ═══════════════════════════════════════════════════════
// UUID
// ═══════════════════════════════════════════════════════
function uuid() {
  return crypto.randomUUID ? crypto.randomUUID() :
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

// ═══════════════════════════════════════════════════════
// LOGGING
// ═══════════════════════════════════════════════════════
const logEntries = [];

function log(level, message) {
  const now = new Date();
  const ts = now.toTimeString().slice(0, 8);
  logEntries.push({ ts, level, message });
  if (logEntries.length > 5000) logEntries.shift();

  const list = document.getElementById('logList');
  const div = document.createElement('div');
  div.className = 'log-item ' + level;
  div.textContent = `[${ts}] [${level}] ${message}`;
  list.appendChild(div);
  list.scrollTop = list.scrollHeight;
}

function clearLog() {
  logEntries.length = 0;
  document.getElementById('logList').innerHTML = '';
  log('INFO', 'Log cleared');
}

// ═══════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════
let generatedPhones = [];
let allContacts = [];
let selectedIds = new Set();
let importMode = null; // 'txt' or 'csv'

// ═══════════════════════════════════════════════════════
// UI HELPERS
// ═══════════════════════════════════════════════════════
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-' + name));
  if (name === 'contacts') refreshContacts();
  if (name === 'log') {
    const list = document.getElementById('logList');
    list.scrollTop = list.scrollHeight;
  }
}

function toggleMenu() {
  document.getElementById('dropdownMenu').classList.toggle('hidden');
}

function showToast(msg, duration = 2500) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add('hidden'), duration);
}

function showDialog(title, body, buttons) {
  document.getElementById('dialogTitle').textContent = title;
  document.getElementById('dialogBody').textContent = body;
  const acts = document.getElementById('dialogActions');
  acts.innerHTML = '';
  buttons.forEach(b => {
    const btn = document.createElement('button');
    btn.className = 'btn ' + (b.class || 'outline');
    btn.textContent = b.text;
    btn.onclick = () => { document.getElementById('dialog').classList.add('hidden'); if (b.action) b.action(); };
    acts.appendChild(btn);
  });
  document.getElementById('dialog').classList.remove('hidden');
}

function closeDialog(e) {
  if (e.target.classList.contains('dialog-overlay')) {
    document.getElementById('dialog').classList.add('hidden');
  }
}

function showProgress(show, pct = 0, label = '') {
  const c = document.getElementById('progressContainer');
  c.style.display = show ? '' : 'none';
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('progressLabel').textContent = label || pct + '%';
}

function setButtonsEnabled(enabled) {
  document.querySelectorAll('.btn-row .btn').forEach(b => {
    if (!b.classList.contains('small')) b.disabled = !enabled;
  });
}

// ═══════════════════════════════════════════════════════
// ACTIONS: Preview
// ═══════════════════════════════════════════════════════
function previewNumbers() {
  const start = document.getElementById('startNumber').value.trim();
  const count = parseInt(document.getElementById('count').value) || 0;
  const step = parseInt(document.getElementById('step').value) || 1;

  if (!normalizePhone(start)) { showToast('❌ Invalid start number'); return; }
  if (count <= 0 || count > 100000) { showToast('❌ Invalid count (1–100000)'); return; }
  if (step <= 0) { showToast('❌ Step must be > 0'); return; }

  try {
    generatedPhones = generateNumbers(start, count, step);
  } catch (err) {
    showToast('❌ ' + err.message);
    return;
  }

  const card = document.getElementById('previewCard');
  card.style.display = '';
  document.getElementById('previewCount').textContent = generatedPhones.length;

  const list = document.getElementById('previewList');
  list.innerHTML = '';
  const show = generatedPhones.slice(0, 100);
  show.forEach((p, i) => {
    const div = document.createElement('div');
    div.className = 'list-item';
    div.innerHTML = `<span class="idx">${i+1}</span><span class="phone">${formatDisplay(p)}</span>`;
    list.appendChild(div);
  });
  if (generatedPhones.length > 100) {
    const div = document.createElement('div');
    div.className = 'list-item';
    div.innerHTML = `<span class="meta">… and ${generatedPhones.length - 100} more</span>`;
    list.appendChild(div);
  }

  log('INFO', `Preview: ${generatedPhones.length} numbers generated`);
  showToast(`✅ ${generatedPhones.length} numbers ready`);
}

// ═══════════════════════════════════════════════════════
// ACTIONS: Generate / Add Contacts
// ═══════════════════════════════════════════════════════
async function generateContacts() {
  if (!generatedPhones.length) {
    previewNumbers();
    if (!generatedPhones.length) return;
  }

  const prefix = document.getElementById('namePrefix').value.trim() || 'Channel Member';
  const phones = [...generatedPhones];
  const total = phones.length;
  let success = 0, failed = 0, skipped = 0;

  setButtonsEnabled(false);
  showProgress(true, 0, `Processing 0/${total}`);
  log('INFO', `Creating ${total} contacts…`);

  // Get existing phones for duplicate check
  const existing = new Set(allContacts.map(c => c.phone));

  const BATCH = 50;
  for (let i = 0; i < total; i++) {
    const phone = phones[i];

    if (existing.has(phone)) {
      skipped++;
    } else {
      const contact = {
        internal_id: uuid(),
        phone: phone,
        generated_name: `${prefix} ${String(success + 1).padStart(3, '0')}`,
        created_at: new Date().toISOString(),
        source: 'generated',
        status: 'active',
        created_by_app: true,
      };
      await dbPut('contacts', contact);
      existing.add(phone);
      success++;
    }

    if ((i + 1) % BATCH === 0 || i === total - 1) {
      const pct = Math.round(((i + 1) / total) * 100);
      showProgress(true, pct, `${i+1}/${total}  ✅${success} ❌${failed} ⏭${skipped}`);
      await new Promise(r => setTimeout(r, 0)); // yield to UI
    }
  }

  log('SUCCESS', `Created ${success}, skipped ${skipped}`);
  showProgress(false);
  setButtonsEnabled(true);
  showToast(`✅ Done: ${success} created, ${skipped} skipped`);
  await refreshContacts();
}

async function addContactsFromPreview() {
  await generateContacts();
}

// ═══════════════════════════════════════════════════════
// ACTIONS: Delete
// ═══════════════════════════════════════════════════════
async function deleteCreated() {
  const created = allContacts.filter(c => c.created_by_app);
  if (!created.length) { showToast('No app-created contacts to delete'); return; }

  showDialog(
    '⚠️ Confirm Delete',
    `Delete ALL ${created.length} contacts created by this application? This cannot be undone. Your original contacts will NOT be affected.`,
    [
      { text: 'Cancel', class: 'outline' },
      { text: 'Delete All', class: 'danger', action: async () => {
        setButtonsEnabled(false);
        showProgress(true, 0, 'Deleting…');
        log('WARNING', `Deleting ${created.length} app-created contacts…`);

        for (let i = 0; i < created.length; i++) {
          await dbDelete('contacts', created[i].internal_id);
          if ((i + 1) % 50 === 0 || i === created.length - 1) {
            const pct = Math.round(((i + 1) / created.length) * 100);
            showProgress(true, pct, `${i+1}/${created.length}`);
            await new Promise(r => setTimeout(r, 0));
          }
        }

        log('SUCCESS', `Deleted ${created.length} contacts`);
        showProgress(false);
        setButtonsEnabled(true);
        showToast(`🗑 Deleted ${created.length} contacts`);
        await refreshContacts();
      }}
    ]
  );
}

async function deleteSelected() {
  if (!selectedIds.size) { showToast('No contacts selected'); return; }

  showDialog(
    '⚠️ Delete Selected',
    `Delete ${selectedIds.size} selected contact(s)? Only app-created contacts will be removed.`,
    [
      { text: 'Cancel', class: 'outline' },
      { text: 'Delete', class: 'danger', action: async () => {
        let deleted = 0;
        for (const id of selectedIds) {
          const c = allContacts.find(x => x.internal_id === id);
          if (c && c.created_by_app) {
            await dbDelete('contacts', id);
            deleted++;
          }
        }
        selectedIds.clear();
        log('SUCCESS', `Deleted ${deleted} selected contacts`);
        showToast(`🗑 Deleted ${deleted} contacts`);
        await refreshContacts();
      }}
    ]
  );
}

// ═══════════════════════════════════════════════════════
// ACTIONS: Import
// ═══════════════════════════════════════════════════════
function importFile(type) {
  importMode = type;
  const input = document.getElementById('fileInput');
  input.accept = type === 'csv' ? '.csv' : '.txt';
  input.value = '';
  input.click();
}

function handleFile(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const text = e.target.result;
    let phones = [];

    if (importMode === 'csv') {
      // Parse CSV — scan all cells for phones
      const rows = text.split('\n').map(r => r.split(','));
      for (const row of rows) {
        for (const cell of row) {
          const trimmed = cell.trim().replace(/"/g, '');
          const norm = normalizePhone(trimmed);
          if (norm) phones.push(norm);
        }
      }
    } else {
      // Parse TXT — one phone per line
      phones = text.split('\n')
        .map(l => l.trim())
        .filter(l => l && !l.startsWith('#'))
        .map(l => normalizePhone(l))
        .filter(Boolean);
    }

    if (!phones.length) {
      showToast('No valid phone numbers found');
      return;
    }

    generatedPhones = phones;
    log('SUCCESS', `Imported ${phones.length} numbers from ${file.name}`);
    showToast(`📥 Imported ${phones.length} numbers`);

    // Show preview
    const card = document.getElementById('previewCard');
    card.style.display = '';
    document.getElementById('previewCount').textContent = phones.length;
    const list = document.getElementById('previewList');
    list.innerHTML = '';
    phones.slice(0, 100).forEach((p, i) => {
      const div = document.createElement('div');
      div.className = 'list-item';
      div.innerHTML = `<span class="idx">${i+1}</span><span class="phone">${formatDisplay(p)}</span>`;
      list.appendChild(div);
    });

    switchTab('generate');
  };
  reader.readAsText(file);
}

// ═══════════════════════════════════════════════════════
// ACTIONS: Export
// ═══════════════════════════════════════════════════════
async function exportTXT() {
  document.getElementById('dropdownMenu').classList.add('hidden');
  const phones = allContacts.filter(c => c.status === 'active').map(c => c.phone);
  if (!phones.length) { showToast('No contacts to export'); return; }

  const text = phones.join('\n') + '\n';
  downloadFile(text, `contacts_${ts()}.txt`, 'text/plain');
  log('SUCCESS', `Exported ${phones.length} contacts as TXT`);
  showToast(`📤 Exported ${phones.length} contacts`);
}

async function exportCSV() {
  document.getElementById('dropdownMenu').classList.add('hidden');
  const phones = allContacts.filter(c => c.status === 'active').map(c => c.phone);
  if (!phones.length) { showToast('No contacts to export'); return; }

  let csv = 'phone,name,source,status,created_at\n';
  allContacts.filter(c => c.status === 'active').forEach(c => {
    csv += `"${c.phone}","${c.generated_name}","${c.source}","${c.status}","${c.created_at}"\n`;
  });
  downloadFile(csv, `contacts_${ts()}.csv`, 'text/csv');
  log('SUCCESS', `Exported ${phones.length} contacts as CSV`);
  showToast(`📤 Exported ${phones.length} contacts`);
}

function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function ts() { return new Date().toISOString().slice(0,19).replace(/[T:]/g,'-'); }

// ═══════════════════════════════════════════════════════
// ACTIONS: Refresh / Clear
// ═══════════════════════════════════════════════════════
async function refreshContacts() {
  allContacts = await dbGetAll('contacts');
  const active = allContacts.filter(c => c.status === 'active');
  const created = active.filter(c => c.created_by_app);

  document.getElementById('statsTotal').textContent = `Total: ${active.length}`;
  document.getElementById('statsCreated').textContent = `Created: ${created.length}`;

  const list = document.getElementById('contactList');
  list.innerHTML = '';

  if (!active.length) {
    list.innerHTML = '<div class="list-item"><span class="meta">No contacts yet</span></div>';
    return;
  }

  active.forEach(c => {
    const div = document.createElement('div');
    div.className = 'list-item contact-item' + (selectedIds.has(c.internal_id) ? ' selected' : '');
    div.onclick = () => toggleSelect(c.internal_id, div);
    div.innerHTML = `
      <input type="checkbox" ${selectedIds.has(c.internal_id) ? 'checked' : ''} onclick="event.stopPropagation(); toggleSelect('${c.internal_id}', this.closest('.contact-item'))">
      <span class="phone">${formatDisplay(c.phone)}</span>
      <span class="meta">${c.generated_name || c.source}</span>
    `;
    list.appendChild(div);
  });
}

function toggleSelect(id, el) {
  if (selectedIds.has(id)) {
    selectedIds.delete(id);
    el.classList.remove('selected');
  } else {
    selectedIds.add(id);
    el.classList.add('selected');
  }
  const cb = el.querySelector('input[type=checkbox]');
  if (cb) cb.checked = selectedIds.has(id);
}

async function clearAllData() {
  document.getElementById('dropdownMenu').classList.add('hidden');
  showDialog(
    '⚠️ Clear All Data',
    'This will permanently delete ALL contacts and logs. Are you sure?',
    [
      { text: 'Cancel', class: 'outline' },
      { text: 'Clear', class: 'danger', action: async () => {
        await dbClear('contacts');
        selectedIds.clear();
        log('WARNING', 'All data cleared');
        showToast('🗑 All data cleared');
        await refreshContacts();
      }}
    ]
  );
}

// ═══════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════
async function init() {
  await openDB();
  log('INFO', 'Application started');
  await refreshContacts();
}

init().catch(err => {
  console.error('Init failed:', err);
  showToast('❌ Failed to initialize database');
});
