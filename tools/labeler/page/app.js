'use strict';
// The labeling page. Every finished crop goes to the server at once (labels/<name>.csv); a crop
// with only its part chosen is kept in localStorage, so closing the tab loses nothing.

const $ = (id) => document.getElementById(id);
const PART_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'q', 'w', 'e'];
const COLOR_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'];
const DOUBTFUL = '';

let S = null; // the server's /api/start: name, crops, answers, parts, colors, other, targets
let index = 0; // the crop on screen
let field = 'part'; // the field the keys answer
let history = []; // saved answers, newest last, for undo: {file, before}
const byPhoto = new Map();
let queue = Promise.resolve();

// Keys and clicks run one at a time, in order, even while a save is on its way.
function enqueue(action) {
  queue = queue.then(action).catch((error) => setStatus(`Gagal: ${error.message}`, 'bad'));
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function setStatus(text, kind = '') {
  $('status').textContent = text;
  $('status').className = kind;
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else if (key === 'style') node.style.cssText = value;
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}

const dataUrl = (path) => '/data/' + path.split('/').map(encodeURIComponent).join('/');
const draftKey = (file) => `legoin-label:${S.name}:${file}`;

// ---- Who is labeling ------------------------------------------------------------------------

async function showLogin() {
  S = null;
  $('login').hidden = false;
  $('work').hidden = true;
  $('who').hidden = true;
  $('overall').textContent = '';
  const { labelers, crops } = await api('/api/labelers');
  $('overall').textContent = `${crops} crop`;
  $('known').replaceChildren();
  if (labelers.length) {
    $('known').append('Lanjutkan sebagai: ');
    for (const name of labelers) {
      const button = el('button', { type: 'button' }, name);
      button.onclick = () => enqueue(() => start(name));
      $('known').append(button);
    }
  }
  $('name-input').value = localStorage.getItem('legoin-label-name') || '';
  $('name-input').focus();
}

async function start(name) {
  try {
    S = await api('/api/start?name=' + encodeURIComponent(name));
  } catch (error) {
    $('login-error').textContent = error.message;
    return;
  }
  $('login-error').textContent = '';
  localStorage.setItem('legoin-label-name', name);
  byPhoto.clear();
  for (const crop of S.crops) {
    if (!byPhoto.has(crop.photo)) byPhoto.set(crop.photo, []);
    byPhoto.get(crop.photo).push(crop);
  }
  history = [];
  buildChoices();
  $('part-target').textContent = `(target ${S.target}, lain ${S.target_other})`;
  $('color-target').textContent = `(target ${S.target}, lain ${S.target_other})`;
  $('name').textContent = name;
  $('login').hidden = true;
  $('work').hidden = false;
  $('who').hidden = false;
  const first = S.crops.findIndex((crop) => !S.answers[crop.file]);
  show(first < 0 ? 0 : first);
}

// ---- Choices ----------------------------------------------------------------------------------

function choiceButton(which, value, key, id, sub, swatch) {
  const button = el('button', { type: 'button', class: 'choice', 'data-field': which, 'data-value': value, title: `${id} · ${sub}` });
  button.append(el('kbd', {}, key));
  if (swatch) button.append(swatch);
  button.append(el('span', { class: 'text' }, el('span', { class: 'id' }, id), el('span', { class: 'sub' }, sub)));
  if (value === DOUBTFUL) button.classList.add('doubtful');
  button.onclick = () => enqueue(() => choose(which, value));
  return button;
}

function buildChoices() {
  $('parts').replaceChildren(
    ...S.parts.map((p, i) => choiceButton('part', p.id, PART_KEYS[i].toUpperCase(), p.id, p.design)),
    choiceButton('part', S.other, 'O', 'lain', 'luar katalog'),
    choiceButton('part', DOUBTFUL, 'X', 'ragu', 'dikosongkan'),
  );
  $('colors').replaceChildren(
    ...S.colors.map((c, i) => choiceButton('color', c.id, COLOR_KEYS[i], c.id, c.name,
      el('i', { class: 'sw', style: `background:#${c.rgb}` }))),
    choiceButton('color', S.other, 'O', 'lain', 'luar katalog', el('i', { class: 'sw other' })),
    choiceButton('color', DOUBTFUL, 'X', 'ragu', 'dikosongkan', el('i', { class: 'sw doubtful' })),
  );
}

// The answer on screen: what was saved, or the part chosen so far.
function draft(file) {
  const pending = localStorage.getItem(draftKey(file));
  if (pending) return JSON.parse(pending);
  return S.answers[file] ? { ...S.answers[file] } : {};
}

async function choose(which, value) {
  const file = S.crops[index].file;
  const answer = draft(file);
  answer[which] = value;
  field = answer.part === undefined ? 'part' : 'color';
  if (answer.part === undefined || answer.color === undefined) {
    localStorage.setItem(draftKey(file), JSON.stringify(answer));
    return render();
  }
  const before = S.answers[file] ? { ...S.answers[file] } : null;
  if (!before || before.part !== answer.part || before.color !== answer.color) {
    localStorage.setItem(draftKey(file), JSON.stringify(answer)); // kept if the save fails
    await save(file, answer.part, answer.color);
    history.push({ file, before });
  }
  // The color is the last step: then on to the next crop nobody has answered yet.
  if (which === 'color') return nextToDo();
  render();
}

async function save(file, part, color) {
  setStatus('Menyimpan…');
  await api('/api/answer', { name: S.name, file, part, color });
  if (part === null) delete S.answers[file];
  else S.answers[file] = { part, color };
  localStorage.removeItem(draftKey(file));
  setStatus(`Tersimpan · ${Object.keys(S.answers).length} crop`, 'ok');
}

async function undo() {
  const file = S.crops[index].file;
  if (localStorage.getItem(draftKey(file))) { // a part chosen but not yet saved
    localStorage.removeItem(draftKey(file));
    field = 'part';
    setStatus('Pilihan dibatalkan');
    return render();
  }
  const last = history.pop();
  if (!last) return setStatus('Tidak ada jawaban untuk diurungkan');
  const { before } = last;
  await save(last.file, before ? before.part : null, before ? before.color : null);
  show(S.crops.findIndex((crop) => crop.file === last.file));
  setStatus(before ? 'Diurungkan: jawaban sebelumnya dipulihkan' : 'Diurungkan: crop kembali belum dilabeli');
}

// ---- Moving between crops ---------------------------------------------------------------------

function show(i) {
  index = Math.max(0, Math.min(i, S.crops.length - 1));
  const answer = draft(S.crops[index].file);
  field = answer.part !== undefined && answer.color === undefined ? 'color' : 'part';
  render();
  for (const crop of S.crops.slice(index + 1, index + 3)) { // load the next ones ahead
    new Image().src = dataUrl(crop.file);
    new Image().src = dataUrl(crop.preview);
  }
}

function nextToDo() {
  const n = S.crops.length;
  for (let k = 1; k <= n; k++) {
    const j = (index + k) % n;
    if (!S.answers[S.crops[j].file]) return show(j);
  }
  show(index + 1); // all answered: keep reviewing in order
}

// ---- Drawing ----------------------------------------------------------------------------------

function render() {
  const crop = S.crops[index];
  const answer = draft(crop.file);
  const done = Object.keys(S.answers).length;

  $('crop').src = dataUrl(crop.file);
  $('photo').src = dataUrl(crop.preview);
  const [w, h] = crop.size;
  const svg = $('boxes');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  const boxes = [];
  for (const other of byPhoto.get(crop.photo)) {
    const [x1, y1, x2, y2] = other.box;
    const rect = { x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
    const attrs = (cls) => Object.entries({ ...rect, class: `box ${cls}` }).map(([k, v]) => `${k}="${v}"`).join(' ');
    if (other === crop) boxes.push(`<rect ${attrs('under')}/><rect ${attrs('current')}/>`);
    else boxes.unshift(`<rect ${attrs('neighbour')}/>`);
  }
  svg.innerHTML = boxes.join('');

  const state = S.answers[crop.file] ? 'sudah dilabeli' : (answer.part !== undefined ? 'part dipilih, warna belum' : 'belum dilabeli');
  $('crop-info').replaceChildren(
    el('b', {}, `Crop ${index + 1} dari ${S.crops.length}`),
    ` · ${crop.session} · ${crop.photo.split('/').pop()} #${crop.n} · ${state}`,
  );
  $('overall').textContent = `${done} / ${S.crops.length} crop dilabeli`;

  for (const which of ['part', 'color']) {
    $(`${which}-field`).classList.toggle('active', field === which);
    for (const button of $(`${which === 'part' ? 'parts' : 'colors'}`).children) {
      button.setAttribute('aria-pressed', String(answer[which] === button.dataset.value));
    }
  }
  $('done').hidden = done < S.crops.length;
  $('done').textContent = `Semua ${S.crops.length} crop sudah kamu labeli. Setelah anggota kedua juga selesai, label kalian dibandingkan dengan merge.`;
  renderProgress();
}

function bars(container, items, key) {
  const counts = new Map();
  for (const answer of Object.values(S.answers)) counts.set(answer[key], (counts.get(answer[key]) || 0) + 1);
  const rows = [];
  for (const item of items) {
    const count = counts.get(item.id) || 0;
    const target = item.target;
    const track = el('span', { class: 'track' + (!target ? ' none' : count >= target ? ' full' : '') },
      el('i', { style: `width:${target ? Math.min(100, (100 * count) / target) : 0}%` }));
    rows.push(el('span', { class: 'label' }, ...(item.swatch ? [item.swatch] : []), item.label), track,
      el('span', { class: 'count' }, target ? `${count}/${target}` : String(count)));
  }
  container.replaceChildren(...rows);
}

function renderProgress() {
  const tail = (sw) => [
    { id: S.other, label: 'lain', target: S.target_other, swatch: sw && el('i', { class: 'sw other' }) },
    { id: DOUBTFUL, label: 'ragu', target: 0, swatch: sw && el('i', { class: 'sw doubtful' }) },
  ];
  bars($('part-progress'), [...S.parts.map((p) => ({ id: p.id, label: p.id, target: S.target })), ...tail(false)], 'part');
  bars($('color-progress'), [
    ...S.colors.map((c) => ({ id: c.id, label: c.id, target: S.target, swatch: el('i', { class: 'sw', style: `background:#${c.rgb}` }) })),
    ...tail(true),
  ], 'color');
}

// ---- Keyboard ---------------------------------------------------------------------------------

function keyValue(key) {
  if (key === 'o') return S.other;
  if (key === 'x') return DOUBTFUL;
  const i = (field === 'part' ? PART_KEYS : COLOR_KEYS).indexOf(key);
  return i < 0 ? undefined : (field === 'part' ? S.parts : S.colors)[i].id;
}

document.addEventListener('keydown', (event) => {
  if (!S || $('work').hidden || event.target.matches('input') || event.altKey || event.metaKey) return;
  const key = event.key.toLowerCase();
  if (event.ctrlKey) {
    if (key === 'z') { event.preventDefault(); enqueue(undo); }
    return;
  }
  const moves = {
    tab: () => { field = field === 'part' ? 'color' : 'part'; render(); },
    arrowleft: () => show(index - 1),
    arrowright: () => show(index + 1),
    n: nextToDo,
    z: undo,
    backspace: undo,
  };
  if (moves[key]) {
    event.preventDefault();
    return enqueue(moves[key]);
  }
  if (['o', 'x', ...PART_KEYS].includes(key)) {
    event.preventDefault();
    // The field is read when the key's turn comes, after the keys typed before it.
    enqueue(() => { const value = keyValue(key); if (value !== undefined) return choose(field, value); });
  }
});

$('login-form').onsubmit = (event) => {
  event.preventDefault();
  enqueue(() => start($('name-input').value.trim().toLowerCase().replace(/\s+/g, '-')));
};
$('switch').onclick = (event) => { event.preventDefault(); enqueue(showLogin); };
$('prev').onclick = () => enqueue(() => show(index - 1));
$('next').onclick = () => enqueue(() => show(index + 1));
$('todo').onclick = () => enqueue(nextToDo);
$('undo').onclick = () => enqueue(undo);
$('part-field').querySelector('legend').onclick = () => { field = 'part'; render(); };
$('color-field').querySelector('legend').onclick = () => { field = 'color'; render(); };
enqueue(showLogin);
