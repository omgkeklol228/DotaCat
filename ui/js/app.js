'use strict';
/* =====================================================================
   DotaCat — логика интерфейса. Без сборки и фреймворков:
   правьте файл и нажмите Ctrl+R в окне программы.
   ===================================================================== */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const debounce = (fn, ms) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); }; };

/* ---------- Связь с программой ---------- */

const TOKEN = (() => {
  const fromUrl = new URLSearchParams(location.search).get('t');
  if (fromUrl) {
    try { sessionStorage.setItem('dotacat-token', fromUrl); } catch { /* приватный режим */ }
    history.replaceState(null, '', location.pathname);
    return fromUrl;
  }
  try { return sessionStorage.getItem('dotacat-token') || ''; } catch { return ''; }
})();

async function api(path, body) {
  const init = { method: body === undefined ? 'GET' : 'POST', headers: { 'X-Token': TOKEN } };
  if (body instanceof Blob) {
    init.body = body;
    init.headers['Content-Type'] = 'application/octet-stream';
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers['Content-Type'] = 'application/json';
  }
  const res = await fetch('/api/' + path, init);
  let data = {};
  try { data = await res.json(); } catch { /* пустой ответ */ }
  if (!res.ok || data.error) throw new Error(data.error || `Ошибка ${res.status}`);
  return data;
}

/* ---------- Справочники ---------- */

const CAT_RU = {
  shaders: 'Шейдеры', 'ti-bp-effects': 'Эффекты TI / BP', heroes: 'Герои', terrains: 'Ландшафты', trees: 'Деревья',
  creeps: 'Крипы', 'creep-deny': 'Денаи', emblems: 'Эмблемы', backgrounds: 'Фоны меню', 'hero-items': 'Предметы героев',
  herofx: 'Эффекты героев', 'hero-sounds': 'Звуки героев', sounds: 'Звуки', wards: 'Варды', couriers: 'Курьеры',
  river: 'Река', 'item-effects': 'Эффекты предметов', 'ranged-attack': 'Дальние атаки', pings: 'Пинги',
  parts: 'Элементы HUD', huds: 'HUD', packs: 'Паки', 'versus-screens': 'Экраны VS', 'mega-kill': 'Мега-киллы',
  announcers: 'Комментаторы', music: 'Музыка', roshan: 'Рошан', ancient: 'Древние', tormentor: 'Терзатели',
  towers: 'Башни', pedestal: 'Пьедесталы', 'high-five': 'Хай-файв', 'item-icons': 'Иконки предметов',
  'hero-icons': 'Иконки героев', ranks: 'Ранги', cursors: 'Курсоры', fonts: 'Шрифты', other: 'Другое',
  optimization: 'Оптимизация', tools: 'Инструменты', guides: 'Гайды', sites: 'Сайты', news: 'Новости', local: 'Свой мод',
};

const FONTS = [
  ['"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif', 'Segoe UI'],
  ['system-ui, sans-serif', 'Системный'],
  ['"Trebuchet MS", sans-serif', 'Trebuchet'],
  ['Verdana, sans-serif', 'Verdana'],
  ['Tahoma, sans-serif', 'Tahoma'],
  ['Georgia, serif', 'Georgia'],
  ['"Cascadia Mono", Consolas, monospace', 'Моноширинный'],
  ['"Comic Sans MS", cursive', 'Comic Sans'],
  ['Impact, sans-serif', 'Impact'],
];

const SOURCES = { d2pfx: 'Dota2PornFx', minify: 'Minify', community: 'Сообщество Minify', local: 'Свой мод' };
const SOURCE_TAGS = { minify: 'MINIFY', community: 'СООБЩЕСТВО' };
const srcOf = (it) => it.source || (it.local ? 'local' : 'd2pfx');

const RATIOS = [['16 / 10', '16:10'], ['16 / 9', '16:9'], ['4 / 3', '4:3'], ['1 / 1', '1:1'], ['3 / 4', '3:4']];

/* Что можно менять во вкладке «Дизайн». [переменная, подпись, тип, мин, макс, шаг, единица] */
const DESIGN_GROUPS = [
  {
    title: 'Цвета', icon: 'palette', items: [
      ['--accent', 'Акцент', 'color'], ['--accent-2', 'Второй акцент (градиент)', 'color'],
      ['--accent-text', 'Текст на кнопках', 'color'], ['--bg', 'Фон окна', 'color'],
      ['--panel', 'Панели', 'color'], ['--card', 'Карточки', 'color'], ['--card-2', 'Вторичный фон', 'color'],
      ['--input', 'Поля ввода', 'color'], ['--border', 'Рамки', 'color'], ['--text', 'Текст', 'color'],
      ['--text-2', 'Вторичный текст', 'color'], ['--muted', 'Приглушённый текст', 'color'],
      ['--success', 'Включено / успех', 'color'], ['--warning', 'Предупреждение', 'color'], ['--danger', 'Удаление / ошибка', 'color'],
    ],
  },
  {
    title: 'Форма и размеры', icon: 'grid', items: [
      ['--radius', 'Скругление углов', 'range', 0, 28, 1, 'px'],
      ['--card-min', 'Ширина карточек', 'range', 150, 420, 5, 'px'],
      ['--gap', 'Расстояние между карточками', 'range', 4, 32, 1, 'px'],
      ['--sidebar-w', 'Ширина боковой панели', 'range', 190, 380, 2, 'px'],
      ['--font-size', 'Размер шрифта', 'range', 12, 18, 0.5, 'px'],
      ['--font', 'Шрифт', 'font'],
      ['--preview-ratio', 'Пропорции превью', 'ratio'],
    ],
  },
  {
    title: 'Прозрачность и фон', icon: 'image', items: [
      ['--panel-alpha', 'Непрозрачность панелей', 'range', 0, 1, 0.02, ''],
      ['--card-alpha', 'Непрозрачность карточек', 'range', 0, 1, 0.02, ''],
      ['--glass-blur', 'Размытие под панелями', 'range', 0, 30, 1, 'px'],
      ['--bg-dim', 'Затемнение фоновой картинки', 'range', 0, 1, 0.05, ''],
      ['--bg-blur', 'Размытие фоновой картинки', 'range', 0, 30, 1, 'px'],
    ],
  },
];
const THEME_VARS = DESIGN_GROUPS.flatMap((g) => g.items.map((i) => i[0])).concat(['--bg-image']);

/* ---------- Состояние ---------- */

const S = {
  cfg: {}, languages: [], status: {}, themes: [], site: '', repo: '', credits: '', paths: {},
  cats: [], items: [], byCat: new Map(), byKey: new Map(), catalogStamp: null, heroes: [], heroFilter: '',
  opt: null, gfx: {}, gfxFps: {},
  installed: [], inst: new Map(),
  view: 'catalog', cat: '__new', group: '', search: '', sort: 'default', onlyInstalled: false,
  styleSel: new Map(), list: [], rendered: 0, pending: new Set(),
  seq: 0, rev: -1, task: null, queue: [], firstPoll: true, offline: false,
  detect: null, modalRefresh: null,
};

const store = {
  get(key, fallback) { try { const v = localStorage.getItem('dotacat-' + key); return v === null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem('dotacat-' + key, JSON.stringify(value)); } catch { /* нет хранилища */ } },
};

/* ---------- Форматирование ---------- */

const catName = (id) => CAT_RU[id] || (S.cats.find((c) => c.id === id) || {}).name_en || id;
const catEmoji = (id) => (S.cats.find((c) => c.id === id) || {}).emoji || (id === 'local' ? '📁' : '🧩');
const plural = (n, one, few, many) => {
  const m10 = n % 10, m100 = n % 100;
  return m10 === 1 && m100 !== 11 ? one : (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many);
};
const fmtCount = (n, one, few, many) => `${n} ${plural(n, one, few, many)}`;
const fmtSize = (bytes) => {
  if (!bytes) return '—';
  const units = ['Б', 'КБ', 'МБ', 'ГБ'];
  let i = 0; let v = bytes;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
};
const fmtDate = (ts) => (ts ? new Date(ts * 1000).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) : '—');
const timeAgo = (ts) => {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return 'только что';
  if (s < 3600) return `${Math.floor(s / 60)} мин назад`;
  if (s < 86400) return `${Math.floor(s / 3600)} ч назад`;
  return fmtDate(ts);
};
const hostOf = (url) => { try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; } };
const isVideo = (url) => /\.(mp4|webm)(\?|$)/i.test(url || '');
const titleOf = (m) => (m.label ? `${m.name} (${m.label})` : m.name);

/* ---------- Уведомления и окна ---------- */

function toast(text, level = 'info', ms = 3800) {
  const el = document.createElement('div');
  el.className = `toast ${level}`;
  el.textContent = text;
  $('#toasts').append(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 260); }, ms);
}

function openModal(html, { cls = '', sticky = false } = {}) {
  const root = $('#modal-root');
  root.innerHTML = `<div class="modal ${cls}" role="dialog" aria-modal="true">
    ${sticky ? '' : `<button class="btn icon-btn modal-close" data-close title="Закрыть">${icon('x')}</button>`}
    <div class="modal-body">${html}</div></div>`;
  root.dataset.sticky = sticky ? '1' : '';
  root.hidden = false;
  return $('.modal-body', root);
}

function closeModal() {
  const root = $('#modal-root');
  root.hidden = true;
  root.innerHTML = '';
  S.modalRefresh = null;
}

function confirmDialog(text, { ok = 'Да', danger = false } = {}) {
  return new Promise((resolve) => {
    const body = openModal(`<div class="modal-pad"><h2>Подтверждение</h2><p class="muted">${esc(text)}</p>
      <div class="row end" style="margin-top:18px"><button class="btn ghost" data-answer="0">Отмена</button>
      <button class="btn ${danger ? 'danger' : 'primary'}" data-answer="1">${esc(ok)}</button></div></div>`, { cls: 'narrow' });
    body.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-answer]');
      if (!btn) return;
      closeModal();
      resolve(btn.dataset.answer === '1');
    });
  });
}

function promptDialog(title, value = '', placeholder = '') {
  return new Promise((resolve) => {
    const body = openModal(`<div class="modal-pad"><h2>${esc(title)}</h2>
      <input class="input" id="prompt-input" style="width:100%;margin-top:10px" value="${esc(value)}" placeholder="${esc(placeholder)}">
      <div class="row end" style="margin-top:18px"><button class="btn ghost" data-answer="0">Отмена</button>
      <button class="btn primary" data-answer="1">Сохранить</button></div></div>`, { cls: 'narrow' });
    const input = $('#prompt-input', body);
    input.focus();
    input.select();
    const done = (ok) => { const v = input.value.trim(); closeModal(); resolve(ok && v ? v : null); };
    body.addEventListener('click', (e) => { const btn = e.target.closest('[data-answer]'); if (btn) done(btn.dataset.answer === '1'); });
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') done(true); });
  });
}

function openUrl(url) {
  api('open', { target: 'url', url }).catch((e) => toast(e.message, 'error'));
}

function openFolder(target) {
  api('open', { target }).catch((e) => toast(e.message, 'error'));
}

/* ---------- Настройки ---------- */

async function saveConfig(patch) {
  Object.assign(S.cfg, patch);
  try {
    const res = await api('config', patch);
    S.cfg = res.config;
    S.status = res.status;
    renderPatchState();
  } catch (e) {
    toast(e.message, 'error');
  }
}
const saveThemeVars = debounce(() => saveConfig({ theme_vars: S.cfg.theme_vars }), 400);

/* ---------- Дизайн: тема, переменные, вид ---------- */

function setThemeLink(id) {
  return new Promise((resolve) => {
    const link = $('#theme-link');
    const href = `themes/${encodeURIComponent(id)}.css`;
    if (link.getAttribute('href') === href) { resolve(); return; }
    link.onload = () => resolve();
    link.onerror = () => resolve();
    link.setAttribute('href', href);
  });
}

function applyOverrides() {
  const vars = S.cfg.theme_vars || {};
  const lines = Object.entries(vars)
    .filter(([k, v]) => /^--[\w-]+$/.test(k) && v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `  ${k}: ${String(v).replace(/[;{}<>]/g, '')};`);
  $('#theme-overrides').textContent = lines.length ? `:root {\n${lines.join('\n')}\n}` : '';
}

function applyLayout() {
  const ui = { card_style: 'classic', sidebar: 'left', glow: true, anim: true, ...(S.cfg.ui || {}) };
  const html = document.documentElement;
  html.dataset.cardStyle = ui.card_style;
  html.dataset.sidebar = ui.sidebar;
  html.dataset.glow = ui.glow ? '1' : '0';
  html.dataset.anim = ui.anim ? '1' : '0';
  $$('#card-style-seg button').forEach((b) => b.classList.toggle('active', b.dataset.style === ui.card_style));
}

async function applyDesign() {
  // файл темы могли удалить вручную — тогда стандартная
  const exists = S.themes.some((t) => t.id === S.cfg.theme);
  await setThemeLink(exists ? S.cfg.theme : 'violet');
  applyOverrides();
  applyLayout();
}

async function loadCustomCss() {
  try {
    const res = await fetch('custom.css', { cache: 'no-store' });
    S.customCss = res.ok ? await res.text() : '';
  } catch { S.customCss = ''; }
  $('#custom-style').textContent = S.customCss;
}

function parseLayout(css) {
  const match = css.match(/@layout([^*]*)\*\//);
  if (!match) return {};
  const out = {};
  for (const [, key, value] of match[1].matchAll(/([\w-]+)="([^"]*)"/g)) {
    const k = key.replace(/-/g, '_');
    out[k] = value === '1' || value === 'true' ? true : value === '0' || value === 'false' ? false : value;
  }
  return out;
}

async function selectTheme(id) {
  let layout = {};
  try { layout = parseLayout(await (await fetch(`themes/${encodeURIComponent(id)}.css`, { cache: 'no-store' })).text()); } catch { /* без раскладки */ }
  S.cfg.theme = id;
  S.cfg.theme_vars = {};
  S.cfg.ui = { ...(S.cfg.ui || {}), ...layout };
  await applyDesign();
  await saveConfig({ theme: id, theme_vars: {}, ui: S.cfg.ui });
  if (S.view === 'design') renderDesign();
}

function setVar(name, value) {
  S.cfg.theme_vars = { ...(S.cfg.theme_vars || {}), [name]: value };
  applyOverrides();
  saveThemeVars();
  const reset = $('[data-design="reset"]');
  if (reset) {
    const n = Object.keys(S.cfg.theme_vars).length;
    reset.disabled = !n;
    reset.lastChild.textContent = ` Сбросить правки (${n})`;
  }
}

function setLayout(patch) {
  S.cfg.ui = { ...(S.cfg.ui || {}), ...patch };
  applyLayout();
  saveConfig({ ui: S.cfg.ui });
  if (S.view === 'design') renderDesign();
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function toHex(color) {
  const ctx = toHex.ctx || (toHex.ctx = document.createElement('canvas').getContext('2d'));
  ctx.fillStyle = '#000000';
  ctx.fillStyle = color || '#000000';
  const v = ctx.fillStyle;
  if (v.startsWith('#')) return v;
  const nums = v.match(/[\d.]+/g) || ['0', '0', '0'];
  return '#' + nums.slice(0, 3).map((n) => Math.round(+n).toString(16).padStart(2, '0')).join('');
}

function buildThemeCss(name) {
  const ui = { card_style: 'classic', sidebar: 'left', glow: true, anim: true, ...(S.cfg.ui || {}) };
  const lines = THEME_VARS.map((v) => [v, cssVar(v)]).filter(([, val]) => val).map(([v, val]) => `  ${v}: ${val};`);
  return `/* @theme name="${name.replace(/"/g, "'")}" author="DotaCat" */\n`
    + `/* @layout card-style="${ui.card_style}" sidebar="${ui.sidebar}" glow="${ui.glow ? 1 : 0}" anim="${ui.anim ? 1 : 0}" */\n\n`
    + `:root {\n${lines.join('\n')}\n}\n`;
}

/* ---------- Каталог: данные ---------- */

const modId = (item, label) => (label ? `${item.key}::${label}` : item.key);

function installedStyle(item) {
  return item.styles.find((s) => S.inst.has(modId(item, s.label))) || null;
}

function selectedStyle(item) {
  if (!item.styles.length) return null;
  const chosen = S.styleSel.get(item.key);
  return item.styles.find((s) => s.label === chosen) || installedStyle(item) || item.styles[0];
}

function isInstalledAny(item) {
  return item.styles.length ? item.styles.some((s) => S.inst.has(modId(item, s.label))) : S.inst.has(item.key);
}

const hay = (item) => item._hay || (item._hay = [item.name, item.group, catName(item.cat), item.cat, ...item.styles.map((s) => s.label)]
  .filter(Boolean).join(' ').toLowerCase());

function passesFilters(item) {
  if (S.cfg.filter_adult && item.adult) return false;
  if (S.cfg.filter_anime && item.anime) return false;
  return true;
}

function filtered() {
  const q = S.search.trim().toLowerCase();
  let list;
  if (S.cat === '__all' || (q && S.cat === '__new')) list = S.items.filter((it) => it.kind !== 'pack');
  else if (S.cat === '__new') list = S.items.filter((it) => it.new);
  else if (S.cat === '__ext') list = S.items.filter((it) => srcOf(it) !== 'd2pfx');
  else list = S.byCat.get(S.cat) || [];
  list = list.filter(passesFilters);
  if (S.source) list = list.filter((it) => srcOf(it) === S.source);
  if (S.group) list = list.filter((it) => it.group === S.group);
  if (S.onlyInstalled) list = list.filter(isInstalledAny);
  let sort = S.sort === 'default' && S.cat === '__new' ? 'new' : S.sort;
  for (const token of q.split(/\s+/).filter(Boolean)) {
    if (token.startsWith('by:') || token.startsWith('@')) {
      const v = token.replace(/^(by:|@)/, '');
      if (v) list = list.filter((it) => [...it.authors, ...it.senders].some((a) => a.toLowerCase().includes(v)));
    } else if (token.startsWith('tag:')) {
      const v = token.slice(4);
      list = list.filter((it) => it.tags.some((t) => t.toLowerCase().includes(v)));
    } else if (token.startsWith('sort:')) {
      sort = token.slice(5);
    } else {
      list = list.filter((it) => hay(it).includes(token));
    }
  }
  if (sort === 'name' || sort === 'a-z') list = [...list].sort((a, b) => a.name.localeCompare(b.name, 'ru'));
  else if (sort === 'z-a') list = [...list].sort((a, b) => b.name.localeCompare(a.name, 'ru'));
  else if (sort === 'new') list = [...list].sort((a, b) => (b.date || 0) - (a.date || 0));
  else if (sort === 'old') list = [...list].sort((a, b) => (a.date || 0) - (b.date || 0));
  return list;
}

async function loadCatalog() {
  if (S.catalogLoading) return;
  S.catalogLoading = true;
  $('#grid').innerHTML = '';
  $('#empty').hidden = false;
  $('#empty').innerHTML = '<div class="big"><span class="spin" style="display:inline-block;width:28px;height:28px"></span></div>Загружаю каталог Dota2PornFx…';
  try {
    const data = await api('catalog');
    S.cats = data.categories;
    S.items = data.items;
    S.heroes = data.heroes || [];
    S.catalogStamp = data.refreshed;
    S.byCat = new Map();
    S.byKey = new Map();
    for (const item of S.items) {
      if (!S.byCat.has(item.cat)) S.byCat.set(item.cat, []);
      S.byCat.get(item.cat).push(item);
      if (!S.byKey.has(item.key)) S.byKey.set(item.key, item);
    }
    if (!['__new', '__all', '__ext'].includes(S.cat) && !S.byCat.has(S.cat)) S.cat = '__new';
    renderCats();
    renderCatalog();
    if (S.view === 'packs') renderPacks();
  } catch (e) {
    $('#empty').innerHTML = `<div class="big">📡</div>${esc(e.message)}<br><button class="btn" id="retry-catalog">${icon('refresh')} Повторить</button>`;
    $('#retry-catalog').onclick = loadCatalog;
  } finally {
    S.catalogLoading = false;
  }
}

/* ---------- Каталог: отрисовка ---------- */

function mediaHTML(url, { autoplay = false, emoji = '🧩' } = {}) {
  if (!url) return `<div class="ph">${emoji}</div>`;
  if (isVideo(url)) {
    return `<video src="${esc(url)}" muted loop playsinline preload="metadata" ${autoplay ? 'autoplay' : ''}></video>`;
  }
  return `<img src="${esc(url)}" alt="" loading="lazy" decoding="async" onerror="this.outerHTML='<div class=&quot;ph&quot;>${emoji}</div>'">`;
}

function cardState(item) {
  const style = selectedStyle(item);
  const id = modId(item, style && style.label);
  return { style, id, inst: S.inst.get(id), busy: S.pending.has(id) };
}

function cardSig(item) {
  const { style, inst, busy } = cardState(item);
  return [style ? style.label : '', inst ? (inst.enabled ? 'on' : 'off') : '-', inst && inst.update ? 'u' : '', busy ? 'b' : '', isInstalledAny(item) ? 'a' : ''].join('|');
}

function actionsHTML(item, { inst, busy }) {
  if (item.kind === 'link') return `<button class="btn sm ghost block" data-act="open-site">${icon('external')} Открыть</button>`;
  if (item.kind === 'pack') return `<button class="btn sm primary block" data-act="pack">${icon('download')} Пак: ${fmtCount(item.pack.length, 'мод', 'мода', 'модов')}</button>`;
  if (busy) return '<button class="btn sm block" disabled><span class="spin"></span> В очереди…</button>';
  if (!inst) return `<button class="btn sm primary block" data-act="install">${icon('download')} Установить</button>`;
  return `<label class="switch" title="Включить / выключить"><input type="checkbox" data-act="toggle" ${inst.enabled ? 'checked' : ''}><span></span></label>
    <span class="on-label">${inst.enabled ? 'Включён' : 'Выключен'}</span>
    <span class="push"></span>
    ${inst.update ? `<button class="btn sm icon-btn" data-act="update" title="Обновить">${icon('refresh')}</button>` : ''}
    <button class="btn sm ghost danger icon-btn" data-act="remove" title="Удалить">${icon('trash')}</button>`;
}

function cardHTML(item) {
  const state = cardState(item);
  const { style, inst } = state;
  const preview = (style && style.preview) || item.preview;
  const cls = ['card'];
  if (inst) cls.push(inst.enabled ? 'is-on' : 'is-off');
  const badges = [];
  if (item.new) badges.push('<span class="tag new">NEW</span>');
  if (item.adult) badges.push('<span class="tag adult">18+</span>');
  if (item.anime) badges.push('<span class="tag anime">ANIME</span>');
  if (inst && inst.update) badges.push('<span class="tag upd">ОБНОВЛЕНИЕ</span>');
  if (SOURCE_TAGS[srcOf(item)]) badges.push(`<span class="tag src" title="Источник: ${esc(SOURCES[srcOf(item)])}">${SOURCE_TAGS[srcOf(item)]}</span>`);
  if (item.dupes && item.dupes.length) {
    const names = item.dupes.map((k) => S.byKey.get(k)).filter(Boolean).map((d) => `${d.name} (${SOURCES[srcOf(d)]})`);
    badges.push(`<span class="tag dupe" title="Похожий мод в другом источнике: ${esc(names.join(', '))}">ЕСТЬ ДУБЛЬ</span>`);
  }
  const who = item.authors.length ? `by ${item.authors.join(', ')}` : (item.senders.length ? `от ${item.senders.join(', ')}` : '');
  const meta = [S.cat === '__new' || S.cat === '__all' ? catName(item.cat) : '', item.group, who].filter(Boolean).join(' · ');
  const styles = item.styles.length > 1
    ? `<div class="styles">${item.styles.map((s) => `<button class="style-dot${style && s.label === style.label ? ' active' : ''}${S.inst.has(modId(item, s.label)) ? ' has' : ''}" style="--dot:${esc(s.color || 'var(--accent)')}" data-act="style" data-label="${esc(s.label)}" title="${esc(s.label)}"></button>`).join('')}<span class="style-label">${esc(style.label)}</span></div>`
    : '';
  const mark = inst ? `<span class="inst-mark${inst.enabled ? '' : ' off'}" title="${inst.enabled ? 'Установлен и включён' : 'Установлен, выключен'}">${icon(inst.enabled ? 'check' : 'x')}</span>` : '';
  return `<article class="${cls.join(' ')}" data-i="${item.i}" data-sig="${esc(cardSig(item))}">
    <div class="card-media" data-act="details">${mediaHTML(preview, { emoji: catEmoji(item.cat) })}<div class="badges">${badges.join('')}</div>${mark}</div>
    <div class="card-body"><div class="card-title" data-act="details" title="${esc(item.name)}">${esc(item.name)}</div>
      <div class="card-meta">${esc(meta || catName(item.cat))}</div>${styles}</div>
    <div class="card-actions">${actionsHTML(item, state)}</div>
  </article>`;
}

const PAGE = 72;

function renderCatalog(reset = true) {
  const grid = $('#grid');
  if (reset) {
    S.list = filtered();
    S.rendered = 0;
    grid.innerHTML = '';
    renderCatalogHead();
    renderHeroPicker();
  }
  const next = S.list.slice(S.rendered, S.rendered + PAGE);
  grid.insertAdjacentHTML('beforeend', next.map(cardHTML).join(''));
  S.rendered += next.length;
  const empty = $('#empty');
  empty.hidden = S.list.length > 0;
  if (!S.list.length) {
    const everywhere = S.search && S.cat !== '__all' && S.cat !== '__new'
      ? `<br><button class="btn" id="search-all">${icon('globe')} Искать во всех модах</button>` : '';
    empty.innerHTML = S.items.length
      ? `<div class="big">🔍</div>Ничего не найдено${S.search ? ` по запросу «${esc(S.search)}»` : ''}.${everywhere}`
      : '<div class="big">📦</div>Каталог пуст.';
    const btn = $('#search-all');
    if (btn) btn.onclick = () => selectCategory('__all');
  }
  requestAnimationFrame(fillViewport);
}

/* IntersectionObserver не срабатывает повторно, пока «маяк» виден — догружаем сами */
function fillViewport() {
  if (S.view !== 'catalog' || S.rendered >= S.list.length) return;
  const content = $('#content');
  if ($('#sentinel').getBoundingClientRect().top < content.getBoundingClientRect().bottom + 900) renderCatalog(false);
}

function renderCatalogHead() {
  let title;
  if (S.cat === '__new') title = S.search ? 'Поиск по всем модам' : 'Новинки';
  else if (S.cat === '__all') title = 'Все моды';
  else if (S.cat === '__ext') title = '🧩 Minify и сообщество';
  else title = `${catEmoji(S.cat)} ${catName(S.cat)}`;
  $('#cat-title').textContent = title;
  const cat = S.cats.find((c) => c.id === S.cat);
  const total = S.list.length;
  let sub = fmtCount(total, 'мод', 'мода', 'модов');
  if (cat && cat.kind === 'link') sub += ' · гайды и ссылки, открываются на сайте';
  if (cat && cat.id === 'cursors') sub += ' · курсор копируется в папку игры (с резервной копией)';
  $('#cat-sub').textContent = sub;

  const groups = $('#groups');
  const names = cat && !cat.heroes ? cat.groups : [];
  if (!names.length) { groups.innerHTML = ''; return; }
  if (names.length > 14) {
    groups.innerHTML = `<select class="input" id="group-select"><option value="">Все (${names.length})</option>${names.map((g) => `<option ${g === S.group ? 'selected' : ''}>${esc(g)}</option>`).join('')}</select>`;
    $('#group-select').onchange = (e) => { S.group = e.target.value; renderCatalog(); };
  } else {
    groups.innerHTML = [`<button class="chip${S.group ? '' : ' active'}" data-group="">Все</button>`]
      .concat(names.map((g) => `<button class="chip${g === S.group ? ' active' : ''}" data-group="${esc(g)}">${esc(g)}</button>`)).join('');
  }
}

/* ---------- Выбор героя (Герои, Предметы героев, Звуки героев…) ---------- */

const heroCategory = (id) => { const c = S.cats.find((x) => x.id === id); return !!(c && c.heroes); };
const heroInfo = (name) => S.heroes.find((h) => h.name === name) || { name, portrait: null };

function heroPortrait(name, cls = '') {
  const hero = heroInfo(name);
  const first = S.items.find((it) => it.group === name && it.preview && !isVideo(it.preview));
  const fallback = first ? first.preview : '';
  if (!hero.portrait && !fallback) return `<div class="ph ${cls}">${esc(name.slice(0, 2))}</div>`;
  const onerror = fallback ? `this.onerror=null;this.src='${esc(fallback)}'` : "this.outerHTML='<div class=&quot;ph&quot;>🧩</div>'";
  return `<img class="${cls}" src="${esc(hero.portrait || fallback)}" alt="" loading="lazy" onerror="${onerror}">`;
}

function heroStats(cat) {
  const counts = new Map();
  for (const item of S.byCat.get(cat) || []) {
    if (item.group && passesFilters(item)) counts.set(item.group, (counts.get(item.group) || 0) + 1);
  }
  const active = new Set(S.installed.filter((m) => m.cat === cat && m.enabled && m.group).map((m) => m.group));
  return { counts, active };
}

function heroTilesHTML() {
  const { counts, active } = heroStats(S.cat);
  const q = S.heroFilter.trim().toLowerCase();
  return S.heroes
    .filter((h) => !q || h.name.toLowerCase().includes(q))
    .map((h) => {
      const n = counts.get(h.name) || 0;
      const cls = ['hero-tile', n ? '' : 'none', active.has(h.name) ? 'has' : ''].filter(Boolean).join(' ');
      return `<button class="${cls}" data-hero="${esc(h.name)}" title="${esc(h.name)}${n ? ` — ${n}` : ' — модов нет'}" ${n ? '' : 'disabled'}>
        ${heroPortrait(h.name)}<span class="hn">${esc(h.name)}</span>${n ? `<span class="hc">${n}</span>` : ''}</button>`;
    }).join('') || '<div class="muted">Герой не найден</div>';
}

function heroBarHTML(name) {
  const heroCats = S.cats.filter((c) => c.heroes);
  const links = heroCats.map((c) => {
    const n = (S.byCat.get(c.id) || []).filter((it) => it.group === name && passesFilters(it)).length;
    return n ? `<button class="chip${c.id === S.cat ? ' active' : ''}" data-hero-cat="${c.id}">${esc(catName(c.id))} <span class="n">${n}</span></button>` : '';
  }).join('');
  const mine = S.installed.filter((m) => m.cat === S.cat && m.group === name);
  const on = mine.filter((m) => m.enabled).map(titleOf);
  let current;
  if (S.cat === 'heroes') {
    current = on.length ? `Сейчас на герое: <b>${esc(on.join(', '))}</b>` : 'Скин не выбран — в игре стандартный вид. На героя можно включить только один скин.';
  } else {
    current = on.length ? `Включено: <b>${esc(on.join(', '))}</b>` : 'Из этого раздела на героя ничего не установлено.';
  }
  return `<div class="hero-bar">
    <button class="btn sm ghost" data-hero="">${icon('back')} Все герои</button>
    ${heroPortrait(name)}
    <div class="hb-info"><h2>${esc(name)}</h2><div class="hero-current">${current}</div><div class="links">${links}</div></div>
  </div>`;
}

function renderHeroPicker() {
  const el = $('#hero-picker');
  if (!heroCategory(S.cat) || S.search.trim()) {
    el.hidden = true;
    el.innerHTML = '';
    return;
  }
  el.hidden = false;
  if (S.group) {
    el.innerHTML = heroBarHTML(S.group);
    return;
  }
  const collapsed = store.get('heroes-collapsed', false);
  el.innerHTML = `<div class="hero-tools">
      <input class="input" id="hero-filter" placeholder="Найти героя…" value="${esc(S.heroFilter)}" autocomplete="off">
      <span class="muted">Выберите героя, чтобы увидеть все моды на него</span><span class="spacer"></span>
      <button class="btn sm ghost" data-hero-collapse>${icon(collapsed ? 'down' : 'up')} ${collapsed ? 'Показать всех' : 'Свернуть'}</button>
    </div>
    <div class="hero-grid${collapsed && !S.heroFilter ? ' collapsed' : ''}" id="hero-grid">${heroTilesHTML()}</div>`;
}

function selectHero(name, cat = S.cat) {
  S.cat = cat;
  S.group = name;
  store.set('cat', cat);
  $$('#cats .cat').forEach((el) => el.classList.toggle('active', el.dataset.cat === cat));
  renderCatalog();
  $('#content').scrollTop = 0;
}

function bindHeroPicker() {
  const el = $('#hero-picker');
  el.addEventListener('click', (e) => {
    const tile = e.target.closest('[data-hero]');
    if (tile) { selectHero(tile.dataset.hero); return; }
    const link = e.target.closest('[data-hero-cat]');
    if (link) { selectHero(S.group, link.dataset.heroCat); return; }
    if (e.target.closest('[data-hero-collapse]')) {
      store.set('heroes-collapsed', !store.get('heroes-collapsed', false));
      renderHeroPicker();
    }
  });
  el.addEventListener('input', (e) => {
    if (e.target.id !== 'hero-filter') return;
    S.heroFilter = e.target.value;
    const grid = $('#hero-grid');
    grid.innerHTML = heroTilesHTML();
    grid.classList.toggle('collapsed', store.get('heroes-collapsed', false) && !S.heroFilter);
  });
}

function updateCards(only) {
  const cards = only ? $$(`#grid .card[data-i="${only.i}"], #opt-mods .card[data-i="${only.i}"]`) : $$('#grid .card, #opt-mods .card');
  for (const card of cards) {
    const item = S.items[+card.dataset.i];
    if (!item || (!only && card.dataset.sig === cardSig(item))) continue;
    const tmp = document.createElement('div');
    tmp.innerHTML = cardHTML(item);
    card.replaceWith(tmp.firstElementChild);
  }
}

function renderCats() {
  const count = (list) => list.filter(passesFilters).length;
  const row = (id, emoji, name, n, extra = '') => `<button class="cat${S.cat === id ? ' active' : ''}${extra}" data-cat="${esc(id)}">
    <span class="emoji">${emoji}</span><span class="name">${esc(name)}</span><span class="count">${n}</span></button>`;
  const external = S.items.filter((it) => srcOf(it) !== 'd2pfx');
  const html = [
    row('__new', '✨', 'Новинки', count(S.items.filter((it) => it.new))),
    row('__all', '🌐', 'Все моды', count(S.items.filter((it) => it.kind !== 'pack'))),
  ];
  if (external.length) html.push(row('__ext', '🧩', 'Minify и сообщество', count(external)));
  for (const cat of S.cats) {
    if (cat.id === 'packs') continue;
    html.push(row(cat.id, cat.emoji || '•', catName(cat.id), count(S.byCat.get(cat.id) || []), cat.kind === 'link' ? ' link-cat' : ''));
  }
  $('#cats').innerHTML = html.join('');
}

function selectCategory(id) {
  S.cat = id;
  S.group = '';
  store.set('cat', id);
  $$('#cats .cat').forEach((el) => el.classList.toggle('active', el.dataset.cat === id));
  showView('catalog');
  renderCatalog();
  $('#content').scrollTop = 0;
}

/* ---------- Действия с модами ---------- */

function replaceDialog(item, replaced) {
  const names = replaced.map((r) => `«${r.name}»`).join(', ');
  const lead = item.cat === 'heroes' && item.group
    ? `На ${esc(item.group)} уже стоит ${esc(names)}. На одного героя можно включить только один скин.`
    : `«${esc(item.name)}» не может работать вместе с ${esc(names)}.`;
  return new Promise((resolve) => {
    const body = openModal(`<div class="modal-pad"><h2>Заменить?</h2><p class="muted">${lead}</p>
      <div class="row end wrap" style="margin-top:18px">
        <button class="btn ghost" data-answer="">Отмена</button>
        <button class="btn" data-answer="disable">Заменить, старый оставить выключенным</button>
        <button class="btn primary" data-answer="remove">${icon('trash')} Заменить и удалить старый</button>
      </div></div>`, { cls: 'narrow' });
    body.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-answer]');
      if (!btn) return;
      closeModal();
      resolve(btn.dataset.answer || null);
    });
  });
}

async function installItem(item) {
  const style = selectedStyle(item);
  const label = style ? style.label : null;
  const id = modId(item, label);
  let removeReplaced = false;
  try {
    const res = await api(`conflicts?key=${encodeURIComponent(item.key)}${label ? `&label=${encodeURIComponent(label)}` : ''}`);
    if (res.similar && res.similar.length) {
      const names = res.similar.map((s) => `«${s.name}» (${s.source})`).join(', ');
      if (!(await confirmDialog(`Похоже, этот мод уже установлен: ${names}. Скорее всего, это тот же мод из другого источника, и вместе они будут перекрывать друг друга. Установить всё равно?`, { ok: 'Установить' }))) return;
    }
    if (res.replace.length) {
      const answer = await replaceDialog(item, res.replace);
      if (!answer) return;
      removeReplaced = answer === 'remove';
    }
  } catch (e) {
    toast(e.message, 'error');
    return;
  }
  S.pending.add(id);
  updateCards(item);
  S.modalRefresh?.();
  try {
    await api('install', { key: item.key, label, remove_replaced: removeReplaced });
  } catch (e) {
    S.pending.delete(id);
    updateCards(item);
    S.modalRefresh?.();
    toast(e.message, 'error');
  }
}

async function removeMod(id, name) {
  if (!(await confirmDialog(`Удалить «${name}»? Файлы мода будут стёрты из папки DotaCat.`, { ok: 'Удалить', danger: true }))) return;
  S.pending.add(id);
  updateCards();
  try { await api('uninstall', { id }); } catch (e) { S.pending.delete(id); toast(e.message, 'error'); }
}

async function toggleMod(id, enabled) {
  try {
    const res = await api('toggle', { id, enabled });
    if (res.disabled && res.disabled.length) toast(`Выключено: ${res.disabled.join(', ')} — вместе они не работают`, 'warn', 5000);
    const mod = S.inst.get(id);
    if (mod) mod.enabled = enabled;
    await refreshInstalled();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function updateMod(id) {
  S.pending.add(id);
  updateCards();
  try { await api('update', { id }); } catch (e) { S.pending.delete(id); toast(e.message, 'error'); }
}

async function installPack(item) {
  try {
    await api('install-pack', { key: item.key });
    toast(`Пак «${item.name}» поставлен в очередь`);
    openLog(true);
  } catch (e) {
    toast(e.message, 'error');
  }
}

function handleItemAction(act, item, el) {
  const { id, inst } = cardState(item);
  switch (act) {
    case 'details': openDetails(item); break;
    case 'style': S.styleSel.set(item.key, el.dataset.label); updateCards(item); S.modalRefresh?.(); break;
    case 'install': installItem(item); break;
    case 'remove': if (inst) removeMod(id, titleOf(inst)); break;
    case 'update': updateMod(id); break;
    case 'open-site': openUrl(item.url || S.site); break;
    case 'pack': installPack(item); break;
    default: break;
  }
}

/* ---------- Карточка мода (подробно) ---------- */

function detailsHTML(item) {
  const state = cardState(item);
  const { style, inst, busy } = state;
  const preview = item.video || (style && style.preview) || item.preview;
  const metaRows = [];
  if (item.authors.length) metaRows.push(['Автор', esc(item.authors.join(', '))]);
  if (item.senders.length) metaRows.push(['Прислал', esc(item.senders.join(', '))]);
  if (item.sources.length) metaRows.push(['Источник', item.sources.map((u) => `<a href="#" data-url="${esc(u)}">${esc(hostOf(u))}</a>`).join(', ')]);
  if (item.tags.length) metaRows.push(['Теги', item.tags.map((t) => `<span class="chip sm">${esc(t)}</span>`).join(' ')]);
  if (item.date) metaRows.push(['Обновлён', fmtDate(item.date)]);
  metaRows.push(['Каталог', esc(SOURCES[srcOf(item)] || srcOf(item))]);
  const dupes = (item.dupes || []).map((k) => S.byKey.get(k)).filter(Boolean);
  if (dupes.length) {
    metaRows.push(['Похожие', dupes.map((d) => `<a href="#" data-dupe="${esc(d.key)}">${esc(d.name)}</a> <span class="muted">(${esc(SOURCES[srcOf(d)])})</span>`).join(', ')]);
  }
  if (inst) metaRows.push(['Размер', fmtSize(inst.size)]);
  if (item.kind === 'pack') metaRows.push(['Состав', item.pack.map(esc).join(', ')]);
  const styles = item.styles.length > 1
    ? `<div class="style-picker">${item.styles.map((s) => `<button class="chip${style && s.label === style.label ? ' active' : ''}" data-act="style" data-label="${esc(s.label)}"><i style="--dot:${esc(s.color || 'var(--accent)')}"></i>${esc(s.label)}${S.inst.has(modId(item, s.label)) ? ' ✓' : ''}</button>`).join('')}</div>`
    : '';
  let actions;
  if (item.kind === 'link') actions = `<button class="btn primary" data-act="open-site">${icon('external')} Открыть</button>`;
  else if (item.kind === 'pack') actions = `<button class="btn primary" data-act="pack">${icon('download')} Установить пак</button>`;
  else if (busy) actions = '<button class="btn" disabled><span class="spin"></span> В очереди…</button>';
  else if (!inst) actions = `<button class="btn primary" data-act="install">${icon('download')} Установить${style ? ` (${esc(style.label)})` : ''}</button>`;
  else {
    actions = `<label class="check"><span class="switch"><input type="checkbox" data-act="toggle" ${inst.enabled ? 'checked' : ''}><span></span></span>${inst.enabled ? 'Включён' : 'Выключен'}</label>
      ${inst.update ? `<button class="btn" data-act="update">${icon('refresh')} Обновить</button>` : ''}
      <button class="btn ghost danger" data-act="remove">${icon('trash')} Удалить</button>`;
  }
  return `<div class="details">
    <div class="details-media">${mediaHTML(preview, { autoplay: true, emoji: catEmoji(item.cat) })}</div>
    <div class="details-info">
      <div class="eyebrow">${catEmoji(item.cat)} ${esc(catName(item.cat))}${item.group ? ` · ${esc(item.group)}` : ''}</div>
      <h2>${esc(item.name)}</h2>
      ${item.description ? `<p class="muted">${esc(item.description)}</p>` : ''}
      ${styles}
      ${metaRows.length ? `<dl class="meta-list">${metaRows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>` : ''}
      <div class="details-actions">${actions}</div>
      <p class="fineprint">Мод из каталога Dota2PornFx. Права на мод принадлежат его автору — <a href="#" data-url="${esc(S.credits)}">список авторов</a>.</p>
    </div></div>`;
}

function openDetails(item) {
  const body = openModal(detailsHTML(item));
  S.modalRefresh = () => {
    const video = $('video', body);
    const time = video ? video.currentTime : 0;
    body.innerHTML = detailsHTML(item);
    const fresh = $('video', body);
    if (fresh && time) fresh.currentTime = time;
  };
  body.addEventListener('click', (e) => {
    const link = e.target.closest('[data-url]');
    if (link) { e.preventDefault(); openUrl(link.dataset.url); return; }
    const dupe = e.target.closest('[data-dupe]');
    if (dupe) { e.preventDefault(); const other = S.byKey.get(dupe.dataset.dupe); if (other) openDetails(other); return; }
    const el = e.target.closest('[data-act]');
    if (!el || el.dataset.act === 'toggle') return;
    handleItemAction(el.dataset.act, item, el);
  });
  body.addEventListener('change', (e) => {
    if (e.target.matches('[data-act="toggle"]')) toggleMod(cardState(item).id, e.target.checked);
  });
}

/* ---------- Установленные ---------- */

function renderInstalled() {
  const list = S.installed;
  const el = $('#inst-list');
  const updates = list.filter((m) => m.update).length;
  const updBtn = $('#btn-update-all');
  updBtn.hidden = !updates;
  updBtn.lastElementChild.textContent = `Обновить все (${updates})`;
  if (!list.length) {
    el.innerHTML = `<div class="empty"><div class="big">📦</div>Пока ничего не установлено.<br>
      <button class="btn primary" data-go="catalog">${icon('grid')} Открыть каталог</button></div>`;
    return;
  }
  el.innerHTML = list.map((m, index) => {
    const thumb = m.preview ? `<img src="${esc(m.preview)}" alt="" loading="lazy">` : `<div class="ph">${catEmoji(m.cat)}</div>`;
    const source = m.local ? '' : SOURCES[srcOf(m)];
    const sub = [m.local ? 'Свой мод' : catName(m.cat), m.group, fmtSize(m.size), source, m.authors && m.authors.length ? `by ${m.authors.join(', ')}` : ''].filter(Boolean).join(' · ');
    return `<div class="inst-row${m.enabled ? '' : ' off'}" draggable="true" data-id="${esc(m.id)}">
      <div class="handle" title="Перетащите, чтобы изменить приоритет">${icon('drag')}</div>
      <div class="prio">${index + 1}</div>
      <div class="inst-thumb" data-act="details">${thumb}</div>
      <div><div class="inst-name">${esc(titleOf(m))} ${m.update ? '<span class="tag upd">ОБНОВЛЕНИЕ</span>' : ''}</div><div class="inst-sub">${esc(sub)}</div></div>
      <div class="inst-actions">
        <button class="btn sm ghost icon-btn" data-act="up" title="Выше (важнее)" ${index === 0 ? 'disabled' : ''}>${icon('up')}</button>
        <button class="btn sm ghost icon-btn" data-act="down" title="Ниже" ${index === list.length - 1 ? 'disabled' : ''}>${icon('down')}</button>
        ${m.update ? `<button class="btn sm" data-act="update">${icon('refresh')} Обновить</button>` : ''}
        <label class="switch" title="${m.enabled ? 'Выключить' : 'Включить'}"><input type="checkbox" data-act="toggle" ${m.enabled ? 'checked' : ''}><span></span></label>
        <button class="btn sm ghost danger icon-btn" data-act="remove" title="Удалить">${icon('trash')}</button>
      </div></div>`;
  }).join('');
}

function saveOrder(ids) {
  const byId = new Map(S.installed.map((m) => [m.id, m]));
  S.installed = ids.map((id) => byId.get(id)).filter(Boolean);
  renderInstalled();
  renderPatchState();
  api('order', { ids }).catch((e) => toast(e.message, 'error'));
}

function bindInstalled() {
  const list = $('#inst-list');
  let dragId = null;
  list.addEventListener('click', (e) => {
    const go = e.target.closest('[data-go]');
    if (go) { showView(go.dataset.go); return; }
    const el = e.target.closest('[data-act]');
    const row = e.target.closest('.inst-row');
    if (!el || !row || el.dataset.act === 'toggle') return;
    const id = row.dataset.id;
    const mod = S.inst.get(id);
    const ids = S.installed.map((m) => m.id);
    const index = ids.indexOf(id);
    switch (el.dataset.act) {
      case 'up': if (index > 0) { ids.splice(index, 1); ids.splice(index - 1, 0, id); saveOrder(ids); } break;
      case 'down': if (index < ids.length - 1) { ids.splice(index, 1); ids.splice(index + 1, 0, id); saveOrder(ids); } break;
      case 'update': updateMod(id); break;
      case 'remove': if (mod) removeMod(id, titleOf(mod)); break;
      case 'details': { const item = mod && S.byKey.get(mod.key); if (item) { if (mod.label) S.styleSel.set(item.key, mod.label); openDetails(item); } break; }
      default: break;
    }
  });
  list.addEventListener('change', (e) => {
    const row = e.target.closest('.inst-row');
    if (row && e.target.matches('[data-act="toggle"]')) toggleMod(row.dataset.id, e.target.checked);
  });
  list.addEventListener('dragstart', (e) => {
    const row = e.target.closest('.inst-row');
    if (!row) return;
    dragId = row.dataset.id;
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragId);
  });
  const clearMarks = () => $$('.inst-row', list).forEach((r) => r.classList.remove('drop-before', 'drop-after'));
  list.addEventListener('dragover', (e) => {
    const row = e.target.closest('.inst-row');
    if (!row || !dragId || row.dataset.id === dragId) return;
    e.preventDefault();
    const rect = row.getBoundingClientRect();
    clearMarks();
    row.classList.add(e.clientY > rect.top + rect.height / 2 ? 'drop-after' : 'drop-before');
  });
  list.addEventListener('drop', (e) => {
    const row = e.target.closest('.inst-row');
    if (!row || !dragId) return;
    e.preventDefault();
    const after = row.classList.contains('drop-after');
    const ids = S.installed.map((m) => m.id).filter((id) => id !== dragId);
    const target = ids.indexOf(row.dataset.id);
    ids.splice(after ? target + 1 : target, 0, dragId);
    clearMarks();
    saveOrder(ids);
  });
  list.addEventListener('dragend', () => { dragId = null; clearMarks(); $$('.inst-row', list).forEach((r) => r.classList.remove('dragging')); });

  $('#btn-import').onclick = () => $('#import-file').click();
  $('#import-file').onchange = async (e) => {
    for (const file of e.target.files) {
      try {
        await api(`import?name=${encodeURIComponent(file.name)}`, file);
        toast(`Добавлен «${file.name}»`, 'success');
      } catch (err) {
        toast(`${file.name}: ${err.message}`, 'error');
      }
    }
    e.target.value = '';
    refreshInstalled();
  };
  $('#btn-check').onclick = runMatchCheck;
  $('#btn-update-all').onclick = () => api('update-all', {}).then(() => openLog(true)).catch((e) => toast(e.message, 'error'));
}

/* ---------- Проверка совпадений ---------- */

const modLabel = (m) => `<b>${esc(m.name)}</b> <span class="muted">(№${m.position}, ${esc(m.source)}${m.enabled ? '' : ', выключен'})</span>`;

function matchReportHTML(r) {
  const s = r.summary;
  const chips = `<div class="report-summary">
      <span class="chip">Одинаковых: <b>${s.identical}</b></span>
      <span class="chip">Конфликтов: <b>${s.conflicts}</b></span>
      <span class="chip">Безвредных пересечений: <b>${s.harmless}</b></span>
      <span class="chip">Похожих из разных источников: <b>${s.similar}</b></span>
    </div>`;
  const sections = [];
  if (r.identical.length) {
    sections.push(`<div class="report-section"><h3>${icon('box')} Одинаковые моды</h3>${r.identical.map((g) => `
      <div class="report-item bad">${g.mods.map(modLabel).join(' = ')}
        <p>Подменяют одни и те же ${fmtCount(g.files, 'файл', 'файла', 'файлов')} с тем же содержимым — это один и тот же мод. Оставьте один.</p>
        <div class="row wrap">${g.mods.slice(1).filter((m) => m.enabled).length ? `<button class="btn sm" data-keep="${esc(g.mods[0].id)}" data-off="${esc(g.mods.slice(1).map((m) => m.id).join('\n'))}">Оставить «${esc(g.mods[0].name)}», остальные выключить</button>` : '<span class="muted">Лишние уже выключены</span>'}</div>
      </div>`).join('')}</div>`);
  }
  const active = r.overlaps.filter((o) => o.active && o.different);
  if (active.length) {
    sections.push(`<div class="report-section"><h3>${icon('info')} Конфликты: разные версии одних файлов</h3>${active.map((o) => `
      <div class="report-item warn">${modLabel(o.a)} перекрывает ${modLabel(o.b)}
        <p>Общих файлов: ${o.shared}, различаются: ${o.different}. В игре будут файлы «${esc(o.a.name)}» — он выше в списке. Чтобы победил другой, перетащите его выше во вкладке «Установленные».</p>
        <ul class="files">${o.examples.map((p) => `<li><code>${esc(p)}</code></li>`).join('')}</ul>
      </div>`).join('')}</div>`);
  }
  const harmless = r.overlaps.filter((o) => !o.different);
  if (harmless.length) {
    sections.push(`<div class="report-section"><h3>${icon('check')} Безвредные пересечения</h3>${harmless.map((o) => `
      <div class="report-item ok">${modLabel(o.a)} и ${modLabel(o.b)}<p>Общих файлов: ${o.shared}, содержимое одинаковое — ничего делать не нужно.</p></div>`).join('')}</div>`);
  }
  const inactive = r.overlaps.filter((o) => !o.active && o.different);
  if (inactive.length) {
    sections.push(`<div class="report-section"><h3>${icon('pause')} Пересечения с выключенными модами</h3>${inactive.map((o) => `
      <div class="report-item">${modLabel(o.a)} и ${modLabel(o.b)}<p>Общих файлов: ${o.shared}${o.rule ? '. Вместе их и так включить нельзя (например, два скина на одного героя)' : ''}.</p></div>`).join('')}</div>`);
  }
  if (r.similar.length) {
    sections.push(`<div class="report-section"><h3>${icon('globe')} Похожие моды из разных источников</h3>${r.similar.map((p) => `
      <div class="report-item${p.identical ? ' bad' : ''}">${modLabel(p.a)} и ${modLabel(p.b)}<p>${p.identical ? 'Содержимое совпадает полностью.' : 'Названия совпадают, а файлы разные: возможно, это разные версии одного мода.'}</p></div>`).join('')}</div>`);
  }
  const body = sections.length ? sections.join('') : `<div class="report-empty"><div class="big">✅</div>Совпадений нет: установленные моды (${r.mods}) не мешают друг другу.</div>`;
  return `<div class="modal-pad"><h2>Проверка совпадений</h2>
    <p class="muted">Сравниваются файлы игры, которые подменяет каждый установленный мод (по CRC32 содержимого), и названия модов из разных источников.</p>
    ${chips}${body}</div>`;
}

async function runMatchCheck() {
  const body = openModal('<div class="modal-pad"><h2>Проверка совпадений</h2><div class="report-empty"><span class="spin" style="display:inline-block;width:26px;height:26px"></span><br>Сравниваю файлы модов…</div></div>');
  let report;
  try {
    report = await api('check-matches');
  } catch (e) {
    body.innerHTML = `<div class="modal-pad"><h2>Проверка совпадений</h2><p class="t-bad">${esc(e.message)}</p></div>`;
    return;
  }
  body.innerHTML = matchReportHTML(report);
  body.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-keep]');
    if (!btn) return;
    btn.disabled = true;
    for (const id of btn.dataset.off.split('\n')) {
      try { await api('toggle', { id, enabled: false }); } catch (err) { toast(err.message, 'error'); }
    }
    await refreshInstalled();
    toast('Лишние копии выключены — нажмите «Применить моды»', 'success');
    body.innerHTML = matchReportHTML(await api('check-matches'));
  });
}

/* ---------- Паки ---------- */

function renderPacks() {
  const packs = S.items.filter((it) => it.kind === 'pack');
  const el = $('#packs');
  if (!packs.length) { el.innerHTML = '<div class="empty">Паков нет.</div>'; return; }
  const haveKeys = new Set(S.installed.map((m) => m.key));
  el.innerHTML = packs.map((p) => {
    const mods = p.pack.map((name) => {
      const it = S.items.find((x) => x.kind === 'mod' && x.name.toLowerCase() === name.toLowerCase());
      const cls = !it ? 'missing' : (haveKeys.has(it.key) ? 'have' : '');
      return `<li class="${cls}">${esc(name)}</li>`;
    }).join('');
    const have = p.pack.filter((name) => { const it = S.items.find((x) => x.kind === 'mod' && x.name.toLowerCase() === name.toLowerCase()); return it && haveKeys.has(it.key); }).length;
    return `<article class="card" data-i="${p.i}">
      <div class="card-media" data-act="details">${mediaHTML(p.preview, { emoji: '🎁' })}</div>
      <div class="card-body"><div class="card-title">${esc(p.name)}</div><div class="card-meta">Установлено ${have} из ${p.pack.length}</div><ul>${mods}</ul></div>
      <div class="card-actions"><button class="btn sm primary block" data-act="pack" ${have === p.pack.length ? 'disabled' : ''}>${icon('download')} ${have === p.pack.length ? 'Всё установлено' : 'Установить пак'}</button></div>
    </article>`;
  }).join('');
}

/* ---------- Настройки ---------- */

async function renderSettings() {
  const c = S.cfg;
  const det = S.detect || {};
  const accounts = det.accounts || [];
  const accountOptions = accounts.length
    ? (c.steam_account ? '' : '<option value="" selected>— выберите аккаунт —</option>')
      + accounts.map((a) => `<option value="${esc(a.id)}" ${a.id === c.steam_account ? 'selected' : ''}>${esc(a.name)}${a.login ? ` (${esc(a.login)})` : ''}${a.recent ? ' — последний' : ''}</option>`).join('')
    : '<option value="">Аккаунты не найдены</option>';
  const lang = S.languages.find((l) => l.id === c.language) || {};
  const pak = `pak${String(c.pak_number).padStart(2, '0')}_dir.vpk`;
  const patch = S.status.patch || {};
  $('#settings').innerHTML = `<div class="panels">
    <section class="panel">
      <h3>${icon('folder')} Игра</h3>
      <p class="hint">Где установлены Steam и Dota 2. Обычно находятся автоматически.</p>
      <div class="field"><label>Папка Steam</label><input class="input" id="set-steam" value="${esc(c.steam_root)}" placeholder="C:\\Program Files (x86)\\Steam"></div>
      <div class="field"><label>Папка Dota 2</label><input class="input" id="set-dota" value="${esc(c.dota_path)}" placeholder="…\\steamapps\\common\\dota 2 beta"></div>
      <div class="field"><label></label><div class="row"><span id="dota-status"></span><span class="spacer"></span><button class="btn sm" data-set="detect">${icon('search')} Найти автоматически</button></div></div>
      <div class="field"><label>Язык игры</label><select class="input" id="set-lang">${S.languages.map((l) => `<option value="${l.id}" ${l.id === c.language ? 'selected' : ''}>${esc(l.name)} → game/${l.folder}</option>`).join('')}</select></div>
      <div class="field"><label>Номер VPK</label><div class="row"><input class="input" type="number" min="2" max="99" id="set-pak" value="${c.pak_number}" style="max-width:90px"><span class="muted">game/${esc(lang.folder || '')}/${pak}</span></div></div>
      ${c.language === 'english' ? '<div class="notice info">Для английского используется папка <code>dota_dutch</code> и параметр <code>-language dutch</code>, а тексты подменяются на английские (как «English Fix» в Minify).</div>' : ''}
    </section>
    <section class="panel">
      <h3>${icon('play')} Параметры запуска</h3>
      <p class="hint">Dota загружает моды из папки языка. DotaCat может сам прописать <code>-language</code> в параметры запуска Steam (Steam ненадолго закроется).</p>
      <div class="field"><label>Аккаунт Steam</label><select class="input" id="set-account">${accountOptions}</select></div>
      <div class="field"><label>Сейчас</label><div class="kv" id="lo-current">…</div></div>
      <div class="field"><label>Нужно</label><div class="kv" id="lo-expected">…</div></div>
      <div class="field"><label></label><div class="row wrap"><label class="check"><input type="checkbox" id="set-restart" ${c.restart_steam ? 'checked' : ''}> Запустить Steam снова</label><span class="spacer"></span><button class="btn sm primary" data-set="apply-lo">${icon('check')} Прописать</button></div></div>
    </section>
    <section class="panel">
      <h3>${icon('grid')} Каталог</h3>
      <p class="hint">Моды берутся с сайта Dota2PornFx (GitHub h6rd/Dota2PornFxWeb).</p>
      <div class="ctrl"><span>Скрывать моды 18+</span><label class="switch"><input type="checkbox" data-cfg="filter_adult" ${c.filter_adult ? 'checked' : ''}><span></span></label></div>
      <div class="ctrl"><span>Скрывать аниме-моды</span><label class="switch"><input type="checkbox" data-cfg="filter_anime" ${c.filter_anime ? 'checked' : ''}><span></span></label></div>
      <div class="ctrl"><span>Обновлять каталог раз в сутки</span><label class="switch"><input type="checkbox" data-cfg="auto_refresh" ${c.auto_refresh ? 'checked' : ''}><span></span></label></div>
      <div class="ctrl"><span>Моды из репозитория Minify<small class="muted" style="display:block">Dark Terrain, Tree Mod, Remove River, Revert Ping Sounds</small></span><label class="switch"><input type="checkbox" data-source-toggle="minify" ${(c.sources || {}).minify !== false ? 'checked' : ''}><span></span></label></div>
      <div class="ctrl"><span>Моды сообщества Minify<small class="muted" style="display:block">Реестр Dota-Modding-Community, архивы проверяются по SHA-512</small></span><label class="switch"><input type="checkbox" data-source-toggle="community" ${(c.sources || {}).community !== false ? 'checked' : ''}><span></span></label></div>
      <div class="ctrl"><span>Обновлён: ${S.catalogStamp ? timeAgo(S.catalogStamp) : '—'} · ${fmtCount(S.items.length, 'запись', 'записи', 'записей')}</span><button class="btn sm" data-set="refresh">${icon('refresh')} Обновить сейчас</button></div>
    </section>
    <section class="panel">
      <h3>${icon('power')} Обслуживание</h3>
      <p class="hint">${patch.time ? `Последнее применение: ${timeAgo(patch.time)}, ${fmtCount((patch.mods || []).length, 'мод', 'мода', 'модов')}.` : 'Моды ещё не применялись.'}</p>
      <div class="row wrap">
        <button class="btn danger" data-set="unpatch">${icon('power')} Убрать моды из игры</button>
        <button class="btn ghost" data-open="game">${icon('folder')} Папка игры</button>
        <button class="btn ghost" data-open="mods">${icon('folder')} Папка модов</button>
        <button class="btn ghost" data-open="data">${icon('folder')} Данные</button>
      </div>
      <p class="hint" style="margin-top:12px">«Убрать моды» удаляет собранный VPK и восстанавливает курсоры — скачанные моды остаются в DotaCat.</p>
    </section>
    <section class="panel wide about">
      <h3>${icon('info')} О программе</h3>
      <p><b>DotaCat ${esc(S.version)}</b> — менеджер модов Dota 2 по образцу <a href="#" data-url="https://github.com/Egezenn/dota2-minify">Minify</a>, работает с каталогом <a href="#" data-url="${esc(S.site)}">Dota2PornFx</a>.</p>
      <p>Моды принадлежат их авторам (<a href="#" data-url="${esc(S.credits)}">список авторов</a>). Программа для личного использования: публиковать её или раздавать каталог без письменного разрешения владельца Dota2PornFx нельзя, продавать моды запрещено.</p>
      <p>Изменение файлов игры — на ваш страх и риск. Моды подключаются через папку языка (как в Minify и на сайте), оригинальные файлы игры не меняются, кроме курсоров (их копия сохраняется).</p>
    </section>
  </div>`;
  updateDotaStatus();
  refreshLaunchInfo();
}

async function updateDotaStatus() {
  const el = $('#dota-status');
  if (!el) return;
  const path = $('#set-dota').value.trim();
  if (!path) { el.innerHTML = '<span class="t-warn">Папка не указана</span>'; return; }
  try {
    const res = await api(`check-dota?path=${encodeURIComponent(path)}`);
    el.innerHTML = res.ok ? `<span class="t-ok">${icon('check')} Dota 2 найдена</span>` : '<span class="t-bad">В этой папке нет Dota 2</span>';
  } catch { el.textContent = ''; }
}

async function refreshLaunchInfo() {
  try {
    const info = await api('launch-options');
    S.launch = info;
    const cur = $('#lo-current');
    const exp = $('#lo-expected');
    if (cur) cur.innerHTML = info.available ? `${esc(info.current || '(пусто)')} ${info.ok ? `<span class="t-ok">✓</span>` : '<span class="t-warn">✗</span>'}` : '<span class="muted">выберите аккаунт</span>';
    if (exp) exp.textContent = info.expected;
    $('#settings-warn').hidden = !(info.available && !info.ok);
  } catch { /* нет Steam */ }
}

async function detectPaths(apply) {
  try {
    S.detect = await api('detect');
    const det = S.detect;
    const patch = {};
    // без кнопки «Найти» заполняем только пустые поля — указанное вручную не трогаем
    if (det.steam_root && (apply || !S.cfg.steam_root)) patch.steam_root = det.steam_root;
    if (det.dota_path && (apply || !S.cfg.dota_path)) patch.dota_path = det.dota_path;
    if (!S.cfg.steam_account && det.accounts.length === 1) patch.steam_account = det.accounts[0].id;
    if (Object.keys(patch).length) await saveConfig(patch);
    if (apply) toast(det.dota_ok ? 'Dota 2 найдена' : 'Dota 2 не найдена — укажите папку вручную', det.dota_ok ? 'success' : 'warn');
  } catch (e) {
    toast(e.message, 'error');
  }
  if (S.view === 'settings') renderSettings();
}

function bindSettings() {
  const root = $('#settings');
  root.addEventListener('change', async (e) => {
    const t = e.target;
    if (t.id === 'set-steam') await saveConfig({ steam_root: t.value });
    else if (t.id === 'set-dota') { await saveConfig({ dota_path: t.value }); updateDotaStatus(); }
    else if (t.id === 'set-lang') { await saveConfig({ language: t.value }); renderSettings(); }
    else if (t.id === 'set-pak') { await saveConfig({ pak_number: +t.value || 66 }); renderSettings(); }
    else if (t.id === 'set-account') { await saveConfig({ steam_account: t.value }); refreshLaunchInfo(); }
    else if (t.id === 'set-restart') await saveConfig({ restart_steam: t.checked });
    else if (t.dataset.sourceToggle) {
      await saveConfig({ sources: { ...(S.cfg.sources || {}), [t.dataset.sourceToggle]: t.checked } });
      await api('catalog/refresh', {});
      toast('Каталог обновляется с новым набором источников…');
    }
    else if (t.dataset.cfg) {
      await saveConfig({ [t.dataset.cfg]: t.checked });
      syncFilterChips();
      renderCats();
      renderCatalog();
    }
  });
  root.addEventListener('click', async (e) => {
    const link = e.target.closest('[data-url]');
    if (link) { e.preventDefault(); openUrl(link.dataset.url); return; }
    const btn = e.target.closest('[data-set]');
    if (!btn) return;
    const act = btn.dataset.set;
    try {
      if (act === 'detect') await detectPaths(true);
      else if (act === 'apply-lo') {
        if (!S.cfg.steam_account) { toast('Выберите аккаунт Steam', 'warn'); return; }
        const line = (S.launch && S.launch.result) || `-language ${S.status.launch_language}`;
        if (!(await confirmDialog(`Прописать в параметры запуска Dota 2: «${line}»? Если Steam открыт, он будет закрыт на пару секунд. Флаги можно выбрать во вкладке «Оптимизация».`, { ok: 'Прописать' }))) return;
        await api('launch-options/apply', { restart: S.cfg.restart_steam });
        S.optReload = true;
        openLog(true);
      } else if (act === 'refresh') { await api('catalog/refresh', {}); toast('Обновляю каталог…'); }
      else if (act === 'unpatch') {
        if (!(await confirmDialog('Убрать все моды из игры? Скачанные моды останутся в DotaCat, их можно применить снова.', { ok: 'Убрать', danger: true }))) return;
        await api('unpatch', {});
        openLog(true);
      }
    } catch (err) {
      toast(err.message, 'error');
    }
  });
}

/* ---------- Вкладка «Дизайн» ---------- */

function controlHTML([name, label, type, min, max, step, unit]) {
  const raw = cssVar(name);
  if (type === 'color') {
    const hex = toHex(raw);
    return `<div class="ctrl"><span>${esc(label)}</span><div class="row">
      <input class="input hex" data-var="${name}" data-kind="hex" value="${esc(hex)}" spellcheck="false">
      <input type="color" data-var="${name}" data-kind="color" value="${esc(hex)}"></div></div>`;
  }
  if (type === 'range') {
    const value = parseFloat(raw) || 0;
    return `<div class="ctrl"><span>${esc(label)}</span><div class="row">
      <input type="range" data-var="${name}" data-kind="range" data-unit="${unit}" min="${min}" max="${max}" step="${step}" value="${value}">
      <span class="val">${value}${unit}</span></div></div>`;
  }
  if (type === 'font') {
    const known = FONTS.some(([v]) => v === raw);
    return `<div class="ctrl"><span>${esc(label)}</span><select class="input" data-var="${name}" data-kind="select">
      ${known ? '' : `<option value="${esc(raw)}" selected>Из темы</option>`}
      ${FONTS.map(([v, n]) => `<option value="${esc(v)}" ${v === raw ? 'selected' : ''} style="font-family:${esc(v)}">${esc(n)}</option>`).join('')}</select></div>`;
  }
  if (type === 'ratio') {
    const norm = raw.replace(/\s+/g, ' ');
    return `<div class="ctrl"><span>${esc(label)}</span><select class="input" data-var="${name}" data-kind="select">
      ${RATIOS.map(([v, n]) => `<option value="${v}" ${v === norm ? 'selected' : ''}>${n}</option>`).join('')}</select></div>`;
  }
  return '';
}

function renderDesign() {
  const ui = { card_style: 'classic', sidebar: 'left', glow: true, anim: true, ...(S.cfg.ui || {}) };
  const seg = (key, options) => `<div class="seg text">${options.map(([v, n]) => `<button data-layout="${key}" data-value="${v}" class="${ui[key] === v ? 'active' : ''}">${n}</button>`).join('')}</div>`;
  const themes = S.themes.map((t) => `<button class="theme-card${t.id === S.cfg.theme ? ' active' : ''}" data-theme="${esc(t.id)}">
      <div class="swatches">${t.colors.filter(Boolean).map((c) => `<i style="background:${esc(c)}"></i>`).join('')}</div>
      <b>${esc(t.name)}</b><small>${t.builtin ? 'встроенная' : 'своя'} · ${esc(t.id)}.css</small>
      ${t.builtin ? '' : `<span class="del" data-del-theme="${esc(t.id)}" title="Удалить тему">${icon('trash')}</span>`}
    </button>`).join('');
  const overrides = Object.keys(S.cfg.theme_vars || {}).length;
  const bg = (S.cfg.theme_vars || {})['--bg-image'];
  $('#design').innerHTML = `<div class="panels">
    <section class="panel wide">
      <h3>${icon('palette')} Темы</h3>
      <p class="hint">Тема — это CSS-файл в папке <code>ui/themes</code>. Скопируйте любой, поменяйте цвета — и он появится здесь.</p>
      <div class="themes">${themes}</div>
      <div class="row wrap" style="margin-top:14px">
        <button class="btn sm primary" data-design="save-theme">${icon('save')} Сохранить текущий вид как тему</button>
        <button class="btn sm" data-design="reset" ${overrides ? '' : 'disabled'}>${icon('undo')} Сбросить правки (${overrides})</button>
        <button class="btn sm ghost" data-design="copy-css">${icon('code')} Скопировать CSS темы</button>
      </div>
    </section>
    <section class="panel">
      <h3>${icon('grid')} Раскладка</h3>
      <p class="hint">Вид карточек и расположение панелей.</p>
      <div class="ctrl"><span>Карточки</span>${seg('card_style', [['classic', 'Классика'], ['overlay', 'Картинка'], ['compact', 'Компактно'], ['list', 'Список']])}</div>
      <div class="ctrl"><span>Боковая панель</span>${seg('sidebar', [['left', 'Слева'], ['right', 'Справа']])}</div>
      <div class="ctrl"><span>Подсветка при наведении</span><label class="switch"><input type="checkbox" data-layout-bool="glow" ${ui.glow ? 'checked' : ''}><span></span></label></div>
      <div class="ctrl"><span>Анимации</span><label class="switch"><input type="checkbox" data-layout-bool="anim" ${ui.anim ? 'checked' : ''}><span></span></label></div>
      <h3 style="margin-top:18px">${icon('image')} Фоновая картинка</h3>
      <p class="hint">JPG, PNG, WEBP или GIF. Затемнение и размытие — в разделе ниже.</p>
      <div class="row wrap">
        <button class="btn sm" data-design="bg-upload">${icon('upload')} Загрузить файл</button>
        <button class="btn sm" data-design="bg-url">${icon('globe')} По ссылке</button>
        <button class="btn sm ghost danger" data-design="bg-clear" ${bg && bg !== 'none' ? '' : 'disabled'}>${icon('x')} Убрать</button>
      </div>
      <input type="file" id="bg-file" accept=".jpg,.jpeg,.png,.webp,.gif" hidden>
    </section>
    ${DESIGN_GROUPS.map((g) => `<section class="panel"><h3>${icon(g.icon)} ${esc(g.title)}</h3>${g.items.map(controlHTML).join('')}</section>`).join('')}
    <section class="panel wide">
      <h3>${icon('code')} Свой CSS</h3>
      <p class="hint">Подключается последним и перекрывает всё. Изменения видны сразу, «Сохранить» записывает файл <code>ui/custom.css</code>.</p>
      <textarea class="input css-editor" id="custom-css" spellcheck="false" placeholder=".card-title { text-transform: uppercase; }">${esc(S.customCss || '')}</textarea>
      <div class="row end" style="margin-top:10px"><button class="btn sm primary" data-design="save-css">${icon('save')} Сохранить</button></div>
    </section>
    <section class="panel wide">
      <h3>${icon('info')} Как полностью переделать интерфейс</h3>
      <ul class="design-help">
        <li><code>ui/index.html</code> — разметка окна (меню, панели, кнопки).</li>
        <li><code>ui/css/base.css</code> — все стили; цвета и размеры берутся из переменных <code>--accent</code>, <code>--card</code> и т.д.</li>
        <li><code>ui/themes/*.css</code> — темы: только значения переменных. Новый файл = новая тема.</li>
        <li><code>ui/js/app.js</code> — логика и шаблоны карточек (функция <code>cardHTML</code>), <code>ui/js/icons.js</code> — иконки.</li>
        <li>Сборка не нужна: сохраните файл и нажмите <b>Ctrl+R</b> в окне программы.</li>
      </ul>
    </section>
  </div>`;
}

function bindDesign() {
  const root = $('#design');
  root.addEventListener('input', (e) => {
    const t = e.target;
    const name = t.dataset.var;
    if (t.id === 'custom-css') { $('#custom-style').textContent = t.value; return; }
    if (!name) return;
    if (t.dataset.kind === 'color') {
      setVar(name, t.value);
      const hex = t.parentElement.querySelector('[data-kind="hex"]');
      if (hex) hex.value = t.value;
    } else if (t.dataset.kind === 'hex') {
      if (/^#[0-9a-f]{6}$/i.test(t.value)) {
        setVar(name, t.value);
        const picker = t.parentElement.querySelector('[data-kind="color"]');
        if (picker) picker.value = t.value;
      }
    } else if (t.dataset.kind === 'range') {
      setVar(name, `${t.value}${t.dataset.unit || ''}`);
      t.nextElementSibling.textContent = `${t.value}${t.dataset.unit || ''}`;
    }
  });
  root.addEventListener('change', (e) => {
    const t = e.target;
    if (t.dataset.kind === 'select') setVar(t.dataset.var, t.value);
    if (t.dataset.layoutBool) setLayout({ [t.dataset.layoutBool]: t.checked });
  });
  root.addEventListener('click', async (e) => {
    const del = e.target.closest('[data-del-theme]');
    if (del) {
      e.stopPropagation();
      if (!(await confirmDialog(`Удалить тему «${del.dataset.delTheme}»?`, { ok: 'Удалить', danger: true }))) return;
      try {
        const res = await api('themes/delete', { id: del.dataset.delTheme });
        S.themes = res.themes;
        if (S.cfg.theme === del.dataset.delTheme) await selectTheme('violet'); else renderDesign();
      } catch (err) { toast(err.message, 'error'); }
      return;
    }
    const theme = e.target.closest('[data-theme]');
    if (theme) { await selectTheme(theme.dataset.theme); return; }
    const layout = e.target.closest('[data-layout]');
    if (layout) { setLayout({ [layout.dataset.layout]: layout.dataset.value }); return; }
    const btn = e.target.closest('[data-design]');
    if (!btn) return;
    const act = btn.dataset.design;
    try {
      if (act === 'save-theme') {
        const current = S.themes.find((t) => t.id === S.cfg.theme);
        const name = await promptDialog('Название новой темы', current && !current.builtin ? current.name : 'Моя тема', 'Например: Неон');
        if (!name) return;
        const res = await api('themes/save', { name, css: buildThemeCss(name) });
        S.themes = res.themes;
        await selectTheme(res.id);
        toast(`Тема «${name}» сохранена в ui/themes/${res.id}.css`, 'success');
      } else if (act === 'reset') {
        S.cfg.theme_vars = {};
        applyOverrides();
        await saveConfig({ theme_vars: {} });
        renderDesign();
      } else if (act === 'copy-css') {
        await navigator.clipboard.writeText(buildThemeCss('Моя тема'));
        toast('CSS темы скопирован в буфер обмена', 'success');
      } else if (act === 'bg-upload') {
        $('#bg-file').click();
      } else if (act === 'bg-url') {
        const url = await promptDialog('Ссылка на картинку', '', 'https://…/wallpaper.jpg');
        if (url) { setVar('--bg-image', `url("${url.replace(/"/g, '%22')}")`); renderDesign(); }
      } else if (act === 'bg-clear') {
        setVar('--bg-image', 'none');
        renderDesign();
      } else if (act === 'save-css') {
        const css = $('#custom-css').value;
        await api('custom-css', { css });
        S.customCss = css;
        toast('Сохранено в ui/custom.css', 'success');
      }
    } catch (err) {
      toast(err.message, 'error');
    }
  });
  root.addEventListener('change', async (e) => {
    if (e.target.id !== 'bg-file' || !e.target.files.length) return;
    const file = e.target.files[0];
    try {
      const res = await api(`background?name=${encodeURIComponent(file.name)}`, file);
      setVar('--bg-image', `url("${res.url}")`);
      if (parseFloat(cssVar('--bg-dim')) > 0.8) setVar('--bg-dim', '0.45');
      renderDesign();
      toast('Фон установлен', 'success');
    } catch (err) {
      toast(err.message, 'error');
    }
  });
}

/* ---------- Вкладка «Оптимизация» ---------- */

const RATING = { good: 'полезно', ok: 'по ситуации', maybe: 'спорно' };
const GROUP_ICONS = { hud: 'monitor', fps: 'gauge', clean: 'sparkles', sound: 'volume' };

function tweakHTML(t) {
  const impact = t.impact ? `<span class="impact" title="Влияние на FPS">${'⚡'.repeat(t.impact)}</span>` : '';
  const settings = t.settings.length && t.enabled
    ? `<div class="sub">${t.settings.map((s) => `<label class="check"><input type="checkbox" data-tweak-setting="${esc(t.id)}" data-key="${esc(s.key)}" ${s.value ? 'checked' : ''}> ${esc(s.label)}</label>`).join('')}</div>`
    : '';
  return `<div class="tweak${t.enabled ? ' on' : ''}">
    <label class="switch"><input type="checkbox" data-tweak="${esc(t.id)}" ${t.enabled ? 'checked' : ''}><span></span></label>
    <div><b>${esc(t.name)}</b>${impact}</div>
    <p>${esc(t.desc)}${t.warn ? ` <span class="warn-text">${esc(t.warn)}</span>` : ''}</p>
    ${settings}
  </div>`;
}

function launchPanelHTML(l) {
  const options = l.options.map((o) => `<label class="opt-check">
      <input type="checkbox" data-launch="${o.id}" ${l.choices[o.id] ? 'checked' : ''}>
      <span><b>${esc(o.name)}</b><span class="rating ${o.rating}">${RATING[o.rating]}</span><code>${esc(o.tokens.join(' '))}</code>
      <p>${esc(o.desc)}</p></span></label>`).join('');
  const renderers = l.renderers.map((r) => `<label class="opt-check">
      <input type="radio" name="renderer" data-renderer="${r.id}" ${l.choices.renderer === r.id ? 'checked' : ''}>
      <span><b>${esc(r.name)}</b>${r.id ? `<code>${r.id}</code>` : ''}<p>${esc(r.desc)}</p></span></label>`).join('');
  let result;
  if (!l.available) result = '<p class="hint">Выберите аккаунт Steam в Настройках — тогда здесь появится текущая строка.</p>';
  else {
    result = `<div class="launch-result"><small class="muted">Сейчас в Steam</small><div class="kv">${esc(l.current || '(пусто)')}</div></div>
      <div class="launch-result"><small class="muted">Будет после «Прописать»</small><div class="kv">${esc(l.result)} ${l.ok ? '<span class="t-ok">✓ уже так</span>' : ''}</div></div>`;
  }
  return `<h3>${icon('play')} Параметры запуска</h3>
    <p class="hint">DotaCat меняет только эти флаги и <code>-language</code>, остальное в строке не трогает.</p>
    ${options}
    <h3 style="margin-top:16px">${icon('monitor')} Графический API</h3>
    ${renderers}
    ${result}
    <div class="row wrap" style="margin-top:12px">
      <label class="check"><input type="checkbox" id="opt-restart" ${S.cfg.restart_steam ? 'checked' : ''}> Запустить Steam снова</label>
      <span class="spacer"></span>
      <button class="btn primary" data-opt="apply-launch" ${l.available && !l.ok ? '' : 'disabled'}>${icon('check')} Прописать в Steam</button>
    </div>`;
}

function graphicsPanelHTML(g) {
  if (!g.available) return `<h3>${icon('monitor')} Графика Dota 2</h3><p class="hint">${esc(g.reason)}</p>`;
  const control = (item) => {
    const changed = Object.prototype.hasOwnProperty.call(S.gfx, item.key);
    const value = changed ? S.gfx[item.key] : item.value;
    let input;
    if (item.type === 'bool') input = `<label class="switch"><input type="checkbox" data-gfx="${item.key}" ${value ? 'checked' : ''}><span></span></label>`;
    else if (item.type === 'select') input = `<select class="input" data-gfx="${item.key}">${item.options.map(([v, n]) => `<option value="${v}" ${String(value) === v ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select>`;
    else {
      const pct = Math.round(Number(value) * 100);
      input = `<div class="row"><input type="range" min="40" max="100" step="1" value="${pct}" data-gfx="${item.key}"><span class="val">${pct}%</span></div>`;
    }
    return `<div class="ctrl${changed ? ' changed' : ''}"><span>${esc(item.name)}${item.desc ? `<small>${esc(item.desc)}</small>` : ''}</span>${input}</div>`;
  };
  const fpsValue = (key) => (S.gfxFps[key] !== undefined ? S.gfxFps[key] : g[key]);
  const fps = g.has_convars ? `
    <div class="ctrl"><span>Лимит FPS в игре<small>0 — без лимита. Лучше ставить чуть ниже частоты монитора или без лимита с Reflex.</small></span>
      <input class="input" type="number" min="0" max="1000" data-fps="fps_max" value="${fpsValue('fps_max') ?? 0}"></div>
    <div class="ctrl"><span>FPS в меню<small>60–120 снимают нагрузку с видеокарты, пока вы в главном меню и поиске.</small></span>
      <input class="input" type="number" min="0" max="1000" data-fps="fps_max_ui" value="${fpsValue('fps_max_ui') ?? 120}"></div>` : '';
  const pending = Object.keys(S.gfx).length + Object.keys(S.gfxFps).length;
  const gpu = g.gpu ? `Видеокарта: <b>${esc(g.gpu.vendor)}</b> · ` : '';
  return `<h3>${icon('monitor')} Графика Dota 2</h3>
    <p class="hint">${gpu}${esc(g.resolution)}${g.refresh ? ` · ${esc(g.refresh)} Гц` : ''}. Настройки из video.txt вашего аккаунта. Меняйте при закрытой игре — она перезаписывает файл при выходе.</p>
    <div class="gfx-head">
      <button class="btn sm primary" data-opt="gfx-preset">${icon('gauge')} Максимум FPS</button>
      <button class="btn sm" data-opt="gfx-reset" ${pending ? '' : 'disabled'}>${icon('undo')} Отменить правки</button>
      <button class="btn sm ghost" data-opt="gfx-restore" ${g.has_backup ? '' : 'disabled'}>${icon('refresh')} Вернуть как было до DotaCat</button>
      <span class="spacer"></span>
      <button class="btn sm primary" data-opt="gfx-save" ${pending ? '' : 'disabled'}>${icon('save')} Сохранить${pending ? ` (${pending})` : ''}</button>
    </div>
    <div class="gfx-grid">${fps}${g.items.map(control).join('')}</div>`;
}

function renderOptimize() {
  const el = $('#optimize');
  const o = S.opt;
  if (!o) { el.innerHTML = '<div class="empty"><span class="spin" style="display:inline-block;width:26px;height:26px"></span></div>'; return; }
  const enabled = o.tweaks.filter((t) => t.enabled).length;
  const g = o.graphics;
  const optMods = S.items.filter((it) => it.cat === 'optimization' && it.kind === 'mod');
  const groups = Object.entries(o.groups).map(([id, title]) => `<section class="panel"><h3>${icon(GROUP_ICONS[id] || 'gauge')} ${esc(title)}</h3>
      ${o.tweaks.filter((t) => t.group === id).map(tweakHTML).join('')}</section>`).join('');
  const tips = o.tips.map((t) => `<div class="tip"><div><b>${esc(t.title)}</b><p>${esc(t.desc)}</p></div>
      ${t.open ? `<button class="btn sm" data-system="${t.open}">${icon('external')} Открыть</button>` : ''}</div>`).join('')
    + (g.available && g.gpu ? `<div class="tip"><div><b>Драйвер ${esc(g.gpu.vendor)}</b><p>Сайт производителя вашей видеокарты.</p></div><button class="btn sm" data-url="${esc(g.gpu.driver_url)}">${icon('external')} Открыть</button></div>` : '');
  el.innerHTML = `<div class="opt-summary">
      <div class="stat ${enabled ? 'good' : ''}"><b>${enabled} из ${o.tweaks.length}</b><span>облегчений эффектов включено</span></div>
      <div class="stat ${o.launch.ok ? 'good' : 'bad'}"><b>${o.launch.ok ? '✓ Готово' : o.launch.available ? 'Не прописаны' : '—'}</b><span>параметры запуска</span></div>
      <div class="stat"><b>${g.available ? esc(g.gpu ? g.gpu.vendor : 'Видеокарта') : '—'}</b><span>${g.available ? `${esc(g.resolution)}${g.refresh ? `, ${esc(g.refresh)} Гц` : ''}` : 'графика недоступна'}</span></div>
    </div>
    <div class="notice info">Облегчения работают как в Minify: стандартные эффекты и звуки заменяются пустышками в том же VPK, что и моды. Включите нужные и нажмите <b>«Применить моды»</b>. Файлы ваших модов они не трогают. Списки — из <a href="#" data-url="${esc(o.minify)}">Minify</a> (robbyz512, Egezenn).</div>
    <div class="panels" style="margin-top:16px">
      ${groups}
      ${optMods.length ? `<section class="panel wide"><h3>${icon('download')} Моды-оптимизации из каталога</h3>
        <p class="hint">Готовые облегчённые VPK с сайта Dota2PornFx.</p><div class="grid opt-mods" id="opt-mods">${optMods.map(cardHTML).join('')}</div></section>` : ''}
      <section class="panel" id="opt-launch">${launchPanelHTML(o.launch)}</section>
      <section class="panel"><h3>${icon('info')} Что не работает</h3>
        <p class="hint">Эти советы до сих пор встречаются в гайдах, но в Dota 2 на Source 2 эффекта не дают — DotaCat их не добавляет.</p>
        <ul class="myths">${o.launch.myths.map(([k, v]) => `<li><code>${esc(k)}</code> — ${esc(v)}</li>`).join('')}</ul>
        <h3 style="margin-top:18px">${icon('sliders')} Порядок действий</h3>
        <ul class="myths">
          <li>Включите облегчения «Больше FPS» и нажмите «Применить моды».</li>
          <li>Пропишите параметры запуска (Vulkan стоит сравнить с DirectX 11 на своём ПК).</li>
          <li>Нажмите «Максимум FPS» в графике и при необходимости верните то, что важно глазу.</li>
          <li>Качество рендера 80–90% — самый большой прирост, если FPS всё ещё мало.</li>
        </ul>
      </section>
      <section class="panel wide" id="opt-graphics">${graphicsPanelHTML(g)}</section>
      <section class="panel wide"><h3>${icon('windows')} Windows и Steam</h3>${tips}</section>
    </div>`;
}

async function loadOptimize() {
  try {
    S.opt = await api('optimize');
  } catch (e) {
    $('#optimize').innerHTML = `<div class="empty"><div class="big">⚠️</div>${esc(e.message)}</div>`;
    return;
  }
  renderTweakCount();
  if (S.view === 'optimize') renderOptimize();
}

function renderTweakCount() {
  const el = $('#count-tweaks');
  const n = S.opt ? S.opt.tweaks.filter((t) => t.enabled).length : 0;
  el.hidden = !n;
  el.textContent = n;
}

function bindOptimize() {
  const root = $('#optimize');
  root.addEventListener('change', async (e) => {
    const t = e.target;
    const card = t.closest('.card');
    if (card && t.matches('[data-act="toggle"]')) { toggleMod(cardState(S.items[+card.dataset.i]).id, t.checked); return; }
    try {
      if (t.dataset.tweak) {
        const res = await api('optimize/tweak', { id: t.dataset.tweak, enabled: t.checked });
        S.opt.tweaks = res.tweaks;
        S.status = res.status;
        renderPatchState();
        renderTweakCount();
        renderOptimize();
      } else if (t.dataset.tweakSetting) {
        const res = await api('optimize/tweak', { id: t.dataset.tweakSetting, settings: { [t.dataset.key]: t.checked } });
        S.opt.tweaks = res.tweaks;
        S.status = res.status;
        renderPatchState();
      } else if (t.dataset.launch || t.dataset.renderer !== undefined) {
        const patch = t.dataset.launch ? { [t.dataset.launch]: t.checked } : { renderer: t.dataset.renderer };
        const info = await api('optimize/launch', patch);
        Object.assign(S.opt.launch, info);
        S.launch = info;
        $('#opt-launch').innerHTML = launchPanelHTML(S.opt.launch);
      } else if (t.id === 'opt-restart') {
        await saveConfig({ restart_steam: t.checked });
      } else if (t.dataset.gfx) {
        const item = S.opt.graphics.items.find((x) => x.key === t.dataset.gfx);
        let value;
        if (item.type === 'bool') value = t.checked;
        else if (item.type === 'select') value = t.value;
        else value = Number(t.value) / 100;
        if (value === item.value || String(value) === String(item.value)) delete S.gfx[item.key]; else S.gfx[item.key] = value;
        $('#opt-graphics').innerHTML = graphicsPanelHTML(S.opt.graphics);
      } else if (t.dataset.fps) {
        const value = Math.max(0, Math.min(1000, Math.round(Number(t.value) || 0)));
        if (value === S.opt.graphics[t.dataset.fps]) delete S.gfxFps[t.dataset.fps]; else S.gfxFps[t.dataset.fps] = value;
        $('#opt-graphics').innerHTML = graphicsPanelHTML(S.opt.graphics);
      }
    } catch (err) {
      toast(err.message, 'error');
    }
  });
  root.addEventListener('input', (e) => {
    if (e.target.type === 'range' && e.target.dataset.gfx) e.target.nextElementSibling.textContent = `${e.target.value}%`;
  });
  root.addEventListener('click', async (e) => {
    const link = e.target.closest('[data-url]');
    if (link) { e.preventDefault(); openUrl(link.dataset.url); return; }
    const system = e.target.closest('[data-system]');
    if (system) { api('open-system', { target: system.dataset.system }).catch((err) => toast(err.message, 'error')); return; }
    const card = e.target.closest('.card');
    const act = e.target.closest('[data-act]');
    if (card && act && act.dataset.act !== 'toggle') { handleItemAction(act.dataset.act, S.items[+card.dataset.i], act); return; }
    const btn = e.target.closest('[data-opt]');
    if (!btn) return;
    const g = S.opt.graphics;
    try {
      if (btn.dataset.opt === 'apply-launch') {
        if (!(await confirmDialog(`Прописать в Steam: «${S.opt.launch.result}»? Если Steam открыт, он закроется на пару секунд.`, { ok: 'Прописать' }))) return;
        await api('launch-options/apply', { restart: S.cfg.restart_steam });
        S.optReload = true;
        openLog(true);
      } else if (btn.dataset.opt === 'gfx-preset') {
        for (const item of g.items) {
          if (item.fps === null || item.fps === undefined) continue;
          if (String(item.fps) === String(item.value)) delete S.gfx[item.key]; else S.gfx[item.key] = item.fps;
        }
        if (g.has_convars && !g.fps_max_ui) S.gfxFps.fps_max_ui = 120;
        $('#opt-graphics').innerHTML = graphicsPanelHTML(g);
        toast('Предустановка выбрана — проверьте и нажмите «Сохранить»');
      } else if (btn.dataset.opt === 'gfx-reset') {
        S.gfx = {};
        S.gfxFps = {};
        $('#opt-graphics').innerHTML = graphicsPanelHTML(g);
      } else if (btn.dataset.opt === 'gfx-save') {
        await api('optimize/graphics', { changes: S.gfx, ...S.gfxFps });
        S.gfx = {};
        S.gfxFps = {};
        openLog(true);
        S.optReload = true;
      } else if (btn.dataset.opt === 'gfx-restore') {
        if (!(await confirmDialog('Вернуть настройки графики, которые были до первого изменения в DotaCat?', { ok: 'Вернуть' }))) return;
        await api('optimize/graphics/restore', {});
        openLog(true);
        S.optReload = true;
      }
    } catch (err) {
      toast(err.message, 'error');
    }
  });
}

/* ---------- Навигация ---------- */

function showView(view) {
  S.view = view;
  $$('.view').forEach((el) => { el.hidden = el.dataset.view !== view; });
  $$('#nav .nav-item').forEach((el) => el.classList.toggle('active', el.dataset.view === view));
  $$('#cats .cat').forEach((el) => el.classList.toggle('active', view === 'catalog' && el.dataset.cat === S.cat));
  if (view === 'installed') renderInstalled();
  if (view === 'packs') renderPacks();
  if (view === 'settings') { renderSettings(); if (!S.detect) detectPaths(false); }
  if (view === 'design') renderDesign();
  if (view === 'optimize') { renderOptimize(); loadOptimize(); }
  $('#content').scrollTop = 0;
}

function syncFilterChips() {
  $('#chip-adult').classList.toggle('active', !!S.cfg.filter_adult);
  $('#chip-anime').classList.toggle('active', !!S.cfg.filter_anime);
  $('#chip-installed').classList.toggle('active', S.onlyInstalled);
}

/* ---------- Состояние патча и задачи ---------- */

function renderNavCounts() {
  const el = $('#count-installed');
  el.textContent = S.installed.length;
  el.classList.toggle('hot', S.installed.some((m) => m.update));
}

function renderPatchState() {
  const enabled = S.installed.filter((m) => m.enabled).map((m) => m.id);
  const patch = (S.status && S.status.patch) || {};
  const applied = patch.mods || [];
  const never = !patch.time;
  const tweaks = (S.status && S.status.tweaks) || [];
  const tweaksChanged = tweaks.join('\n') !== (patch.tweaks || []).join('\n');
  const dirty = (!never && (enabled.join('\n') !== applied.join('\n') || tweaksChanged || (patch.lang && patch.lang !== S.cfg.language)))
    || (never && (enabled.length > 0 || tweaks.length > 0));
  $('#btn-patch').classList.toggle('dirty', dirty);
  const el = $('#patch-state');
  el.classList.toggle('dirty', dirty);
  if (never) el.textContent = enabled.length ? `Включено ${fmtCount(enabled.length, 'мод', 'мода', 'модов')} — нажмите «Применить моды»` : 'Моды ещё не применялись';
  else el.textContent = `Применено ${timeAgo(patch.time)}: ${fmtCount(applied.length, 'мод', 'мода', 'модов')}${dirty ? ' · есть изменения' : ''}`;
}

function renderTask() {
  const t = S.task;
  const bar = $('#progress');
  const text = $('#task-text');
  const queued = S.queue.length ? ` · в очереди: ${S.queue.length}` : '';
  if (S.offline) { bar.hidden = true; text.innerHTML = '<span class="t-bad">Нет связи с программой — перезапустите DotaCat</span>'; return; }
  if (!t) { bar.hidden = true; text.textContent = S.queue.length ? `Ожидание${queued}` : 'Готово'; return; }
  bar.hidden = false;
  const pct = t.total ? Math.min(100, (t.done / t.total) * 100) : 0;
  bar.classList.toggle('indeterminate', !t.total);
  bar.firstElementChild.style.width = t.total ? `${pct}%` : '';
  const label = t.label && !t.title.includes(t.label) ? ` — ${t.label}` : '';
  text.textContent = `${t.title}${label}${t.total ? ` · ${Math.round(pct)}%` : ''}${queued}`;
  $('#btn-patch').disabled = t.title === 'Применение модов';
}

function addLog(entry) {
  const body = $('#log-body');
  const line = document.createElement('div');
  line.className = `log-line ${entry.level}`;
  const time = new Date(entry.t * 1000).toLocaleTimeString('ru-RU');
  line.innerHTML = `<span class="t">${time}</span>${esc(entry.text)}`;
  const atBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 40;
  body.append(line);
  while (body.children.length > 1500) body.firstElementChild.remove();
  if (atBottom) body.scrollTop = body.scrollHeight;
  if (!S.firstPoll) {
    if (entry.level === 'error') toast(entry.text, 'error', 7000);
    else if (entry.level === 'done') toast(entry.text, 'success', 5000);
  }
}

function openLog(show) {
  const panel = $('#log-panel');
  panel.hidden = show === undefined ? !panel.hidden : !show;
  if (!panel.hidden) { const body = $('#log-body'); body.scrollTop = body.scrollHeight; }
}

async function refreshInstalled() {
  try {
    const res = await api('installed');
    S.installed = res.mods;
    S.status = res.status;
    S.inst = new Map(res.mods.map((m) => [m.id, m]));
    for (const id of [...S.pending]) {
      if (S.inst.has(id) || (!S.task && !S.queue.length)) S.pending.delete(id);
    }
    renderNavCounts();
    updateCards();
    renderPatchState();
    if (S.view === 'installed') renderInstalled();
    if (S.view === 'packs') renderPacks();
    if (S.view === 'catalog' && heroCategory(S.cat) && document.activeElement?.id !== 'hero-filter') renderHeroPicker();
    S.modalRefresh?.();
  } catch { /* повторим при следующем опросе */ }
}

async function poll() {
  let delay = 1000;
  try {
    const res = await api(`poll?since=${S.seq}`);
    S.seq = res.seq;
    for (const entry of res.logs) addLog(entry);
    S.task = res.task;
    S.queue = res.queue;
    S.offline = false;
    if (res.rev !== S.rev) {
      S.rev = res.rev;
      await refreshInstalled();
      if (S.optReload && !res.task && !res.queue.length) {
        S.optReload = false;
        loadOptimize();
        refreshLaunchInfo();
      }
    }
    if (S.catalogStamp !== null && res.catalog && res.catalog !== S.catalogStamp) loadCatalog();
    if (!res.task && !res.queue.length) $('#btn-patch').disabled = false;
    delay = res.task || res.queue.length ? 350 : 1000;
  } catch {
    S.offline = true;
    delay = 2500;
  }
  S.firstPoll = false;
  renderTask();
  setTimeout(poll, delay);
}

/* ---------- Первый запуск ---------- */

async function openWizard() {
  let det = {};
  try { det = await api('detect'); S.detect = det; } catch { /* вручную */ }
  const lang = det.language || S.cfg.language || 'russian';
  const accounts = det.accounts || [];
  const body = openModal(`<div class="modal-pad wizard">
    <div class="wizard-hero"><div class="logo big"><i class="logo-cat"></i></div><div>
      <h2>Добро пожаловать в DotaCat</h2>
      <p class="muted">Моды Dota2PornFx в один клик — как в Minify, только с вашим дизайном.</p></div></div>
    <div class="field"><label>Папка Dota 2</label><input class="input" id="wz-dota" value="${esc(det.dota_path || S.cfg.dota_path || '')}" placeholder="…\\steamapps\\common\\dota 2 beta"></div>
    <div class="field"><label>Папка Steam</label><input class="input" id="wz-steam" value="${esc(det.steam_root || S.cfg.steam_root || '')}"></div>
    <div class="field"><label>Язык игры</label><select class="input" id="wz-lang">${S.languages.map((l) => `<option value="${l.id}" ${l.id === lang ? 'selected' : ''}>${esc(l.name)}</option>`).join('')}</select></div>
    <div class="field"><label>Аккаунт Steam</label><select class="input" id="wz-acc">${accounts.map((a) => `<option value="${esc(a.id)}">${esc(a.name)}${a.login ? ` (${esc(a.login)})` : ''}</option>`).join('') || '<option value="">не найден</option>'}</select></div>
    <div class="notice">Изменение файлов игры — на ваш страх и риск. Моды принадлежат их авторам: не выдавайте их за свои и не продавайте. Каталог — <b>Dota2PornFx</b> (h6rd).</div>
    <label class="check"><input type="checkbox" id="wz-ok"> Понимаю и согласен</label>
    <div class="row end"><button class="btn primary" id="wz-go" disabled>${icon('bolt')} Поехали</button></div>
  </div>`, { cls: 'narrow', sticky: true });
  $('#wz-ok', body).onchange = (e) => { $('#wz-go', body).disabled = !e.target.checked; };
  $('#wz-go', body).onclick = async () => {
    await saveConfig({
      setup_done: true,
      dota_path: $('#wz-dota', body).value,
      steam_root: $('#wz-steam', body).value,
      language: $('#wz-lang', body).value,
      steam_account: $('#wz-acc', body).value,
    });
    closeModal();
    toast('Готово! Выберите моды и нажмите «Применить моды».', 'success', 6000);
  };
}

/* ---------- Запуск ---------- */

function bindStatic() {
  fillIcons();
  $('#nav').addEventListener('click', (e) => { const b = e.target.closest('[data-view]'); if (b) showView(b.dataset.view); });
  $('#cats').addEventListener('click', (e) => { const b = e.target.closest('[data-cat]'); if (b) selectCategory(b.dataset.cat); });
  $('#groups').addEventListener('click', (e) => { const b = e.target.closest('[data-group]'); if (b) { S.group = b.dataset.group; renderCatalog(); } });

  const grid = $('#grid');
  grid.addEventListener('click', (e) => {
    const el = e.target.closest('[data-act]');
    const card = e.target.closest('.card');
    if (!el || !card || el.dataset.act === 'toggle') return;
    handleItemAction(el.dataset.act, S.items[+card.dataset.i], el);
  });
  grid.addEventListener('change', (e) => {
    const card = e.target.closest('.card');
    if (card && e.target.matches('[data-act="toggle"]')) toggleMod(cardState(S.items[+card.dataset.i]).id, e.target.checked);
  });
  grid.addEventListener('mouseover', (e) => {
    const video = e.target.closest('.card')?.querySelector('video');
    if (video && video.paused) video.play().catch(() => {});
  });
  grid.addEventListener('mouseout', (e) => {
    const card = e.target.closest('.card');
    if (card && !card.contains(e.relatedTarget)) card.querySelector('video')?.pause();
  });
  $('#packs').addEventListener('click', (e) => {
    const el = e.target.closest('[data-act]');
    const card = e.target.closest('.card');
    if (el && card) handleItemAction(el.dataset.act, S.items[+card.dataset.i], el);
  });

  new IntersectionObserver((entries) => {
    if (entries.some((en) => en.isIntersecting) && S.view === 'catalog' && S.rendered < S.list.length) renderCatalog(false);
  }, { root: $('#content'), rootMargin: '900px' }).observe($('#sentinel'));

  const onSearch = debounce(() => {
    S.search = $('#search').value;
    if (S.view !== 'catalog') showView('catalog');
    renderCatalog();
  }, 160);
  $('#search').addEventListener('input', onSearch);
  $('#sort').addEventListener('change', (e) => { S.sort = e.target.value; store.set('sort', S.sort); renderCatalog(); });
  $('#source-filter').addEventListener('change', (e) => {
    S.source = e.target.value;
    store.set('source', S.source);
    if (S.view !== 'catalog') showView('catalog');
    renderCatalog();
  });

  $('#chip-installed').onclick = () => { S.onlyInstalled = !S.onlyInstalled; syncFilterChips(); renderCatalog(); };
  $('#chip-adult').onclick = async () => { await saveConfig({ filter_adult: !S.cfg.filter_adult }); syncFilterChips(); renderCats(); renderCatalog(); };
  $('#chip-anime').onclick = async () => { await saveConfig({ filter_anime: !S.cfg.filter_anime }); syncFilterChips(); renderCats(); renderCatalog(); };
  $('#card-style-seg').addEventListener('click', (e) => { const b = e.target.closest('[data-style]'); if (b) setLayout({ card_style: b.dataset.style }); });

  $('#btn-patch').onclick = async () => {
    if (!S.status.dota_ok) { toast('Сначала укажите папку Dota 2 в Настройках', 'warn'); showView('settings'); return; }
    try { await api('patch', {}); openLog(true); } catch (e) { toast(e.message, 'error'); }
  };
  $('#btn-play').onclick = () => api('play', {}).then(() => toast('Запускаю Dota 2…')).catch((e) => toast(e.message, 'error'));
  $('#btn-log').onclick = () => openLog();
  $('#log-close').onclick = () => openLog(false);
  $('#log-clear').onclick = () => { $('#log-body').innerHTML = ''; };

  document.addEventListener('click', (e) => {
    const folder = e.target.closest('[data-open]');
    if (folder) openFolder(folder.dataset.open);
  });
  $('#modal-root').addEventListener('click', (e) => {
    if (e.target.closest('[data-close]') || (e.target.id === 'modal-root' && !e.currentTarget.dataset.sticky)) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('#modal-root').hidden && !$('#modal-root').dataset.sticky) closeModal();
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') { e.preventDefault(); $('#search').focus(); }
  });
  window.addEventListener('pagehide', () => navigator.sendBeacon(`/api/bye?t=${encodeURIComponent(TOKEN)}`));

  bindInstalled();
  bindSettings();
  bindDesign();
  bindHeroPicker();
  bindOptimize();
}

async function init() {
  bindStatic();
  let st;
  try {
    st = await api('state');
  } catch (e) {
    $('#empty').hidden = false;
    $('#empty').innerHTML = `<div class="big">🔒</div>${esc(e.message)}`;
    return;
  }
  S.cfg = st.config;
  S.version = st.version;
  S.languages = st.languages;
  S.status = st.status;
  S.themes = st.themes;
  S.site = st.site;
  S.repo = st.repo;
  S.credits = st.credits;
  S.paths = st.paths;
  S.cat = store.get('cat', '__new');
  S.sort = store.get('sort', 'default');
  $('#sort').value = S.sort;
  S.source = store.get('source', '');
  $('#source-filter').value = S.source;
  await applyDesign();
  await loadCustomCss();
  syncFilterChips();
  showView('catalog');
  poll();
  loadCatalog();
  refreshLaunchInfo();
  loadOptimize();
  if (!S.cfg.setup_done) openWizard();
}

init();
