// Pakkeliste sidebar panel. Home Assistant sets .hass/.narrow on this element;
// all API calls go through hass.callApi so they are authenticated.

const STYLE = `
:host { display: block; min-height: 100%; background: var(--bg); color: var(--text);
  --bg: var(--primary-background-color, #f4f5f7); --card: var(--card-background-color, #fff);
  --text: var(--primary-text-color, #1c1e21); --muted: var(--secondary-text-color, #6b7280);
  --line: var(--divider-color, #e3e5e8); --accent: var(--primary-color, #03a9f4);
  --accent-text: var(--text-primary-color, #fff); --done: var(--disabled-text-color, #9ca3af);
  --danger: var(--error-color, #d93025); --ok: var(--success-color, #2e9e5b);
  font: 16px/1.4 var(--paper-font-body1_-_font-family, system-ui, sans-serif); }
* { box-sizing: border-box; }
#app { max-width: 720px; margin: 0 auto; padding: 12px 16px 80px; }
h1 { font-size: 1.4rem; margin: 8px 0; font-weight: 500; }
h2 { font-size: 1.05rem; margin: 0; font-weight: 500; }
button, input, select { font: inherit; color: inherit; }
button { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 8px 14px; cursor: pointer; min-height: 40px; }
button.primary { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
button.danger { color: var(--danger); }
button.ghost { background: transparent; border-color: transparent; }
button.on { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
input[type=text], select { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 8px 12px; min-height: 40px; width: 100%; }
.bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 8px 0; }
.bar .grow { flex: 1; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; margin: 12px 0; overflow: hidden; }
.card-head { display: flex; align-items: center; gap: 8px; padding: 12px 14px; }
.card-head h2 { flex: 1; }
.muted { color: var(--muted); font-size: .9rem; }
.progress { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.progress > div { height: 100%; background: var(--ok); transition: width .2s; }
.trip { display: block; padding: 14px; cursor: pointer; }
.row { display: flex; align-items: center; gap: 10px; padding: 6px 14px; min-height: 52px; border-top: 1px solid var(--line); }
.row .name { flex: 1; word-break: break-word; }
.row.packed .name { text-decoration: line-through; color: var(--done); }
.check { width: 28px; height: 28px; border: 2px solid var(--muted); border-radius: 8px; flex: none; display: grid; place-items: center; color: transparent; font-weight: 700; }
.packed .check { background: var(--ok); border-color: var(--ok); color: #fff; }
.qty { background: var(--line); border-radius: 999px; padding: 2px 10px; font-size: .9rem; font-variant-numeric: tabular-nums; }
.step { display: flex; align-items: center; gap: 4px; }
.step button { min-width: 36px; padding: 4px 0; min-height: 36px; }
.step span { min-width: 24px; text-align: center; font-variant-numeric: tabular-nums; }
.add { display: flex; gap: 8px; padding: 10px 14px; border-top: 1px solid var(--line); }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chip { padding: 2px 10px; min-height: 30px; border-radius: 999px; font-size: .85rem; }
.item-edit { display: flex; flex-direction: column; gap: 6px; padding: 8px 14px; border-top: 1px solid var(--line); }
.item-edit .line { display: flex; gap: 8px; align-items: center; }
.sticky { position: sticky; top: 0; background: var(--bg); padding: 8px 0 4px; z-index: 5; }
.empty { text-align: center; color: var(--muted); padding: 40px 0; }
dialog { border: 1px solid var(--line); border-radius: 14px; background: var(--card); color: var(--text); width: min(92vw, 420px); }
dialog::backdrop { background: rgba(0,0,0,.5); }
label { display: block; margin: 10px 0 4px; font-size: .9rem; color: var(--muted); }
`;

const SHELL = `
<style>${STYLE}</style>
<div id="app"></div>
<dialog id="new-trip">
  <form method="dialog" id="new-trip-form">
    <h2>Ny tur</h2>
    <label for="nt-name">Navn</label>
    <input type="text" id="nt-name" placeholder="fx Sommerhus juli" required>
    <label for="nt-preset">Turtype</label>
    <select id="nt-preset"></select>
    <div class="bar" style="margin-top:16px">
      <span class="grow"></span>
      <button type="button" id="nt-cancel">Annuller</button>
      <button class="primary" type="submit">Opret</button>
    </div>
  </form>
</dialog>`;

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const QTY_RE = /^(.*?)\s*(?:\((\d+)\)|[x×](\d+))\s*$/i;
// "Shorts (7)" or "Håndklæder x2" -> {name, qty}
function parseItem(t) {
  t = t.trim();
  const m = QTY_RE.exec(t);
  return m && m[1] ? { name: m[1].trim(), qty: +(m[2] || m[3]) } : { name: t, qty: 1 };
}
const num = v => +v;
const newId = () => Math.random().toString(16).slice(2, 10);

class PackingListPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' }).innerHTML = SHELL;
    this._started = false;
    this._narrow = false;
    this.S = null;        // {presets, template, trips(summaries)}
    this.trip = null;     // currently open trip (full)
    this.nav = { view: 'list' };
    this.ui = { edit: false, hide: false, collapsed: {} };
    try { this.ui.hide = localStorage.getItem('packing_hide') === '1'; } catch (e) { /* storage unavailable */ }
    this._saveTimer = null;
  }

  set hass(h) {
    this._hass = h;
    if (!this._started) { this._started = true; this._bind(); this.go(); }
  }
  set narrow(n) { this._narrow = n; this._menu(); }
  set route(_) {}
  set panel(_) {}

  connectedCallback() { this._poll = setInterval(() => this.poll(), 4000); }
  disconnectedCallback() { clearInterval(this._poll); }

  // ---------- plumbing ----------
  async api(method, path, body) {
    return this._hass.callApi(method, 'packing_list/' + path, body);
  }
  fail(e) { alert('Fejl: ' + (e.message || (e.body && e.body.message) || e.body || e)); }
  $(id) { return this.shadowRoot.getElementById(id); }
  get app() { return this.$('app'); }

  async go() {
    try {
      if (this.nav.view === 'trip') {
        this.trip = await this.api('GET', 'trips/' + this.nav.id);
        this.ui.edit = false;
      } else {
        this.trip = null;
        this.S = await this.api('GET', 'state');
      }
    } catch (e) {
      // trip deleted elsewhere, or a transient failure: fall back to the list
      this.trip = null; this.nav = { view: 'list' };
      try { this.S = await this.api('GET', 'state'); } catch (x) { this.fail(x); return; }
    }
    this.render();
  }
  navigate(view, id) { this.nav = { view, id }; this.go(); }

  render() {
    const v = this.nav.view;
    this.app.innerHTML = v === 'trip' && this.trip ? this.tripView() : v === 'template' ? this.templateView() : this.listView();
    this._menu();
  }
  _menu() {
    const m = this.shadowRoot.querySelector('ha-menu-button');
    if (m) { m.hass = this._hass; m.narrow = this._narrow; }
  }

  // ---------- trip list ----------
  listView() {
    const trips = [...this.S.trips].sort((a, b) => b.created.localeCompare(a.created));
    return `
      <div class="bar"><ha-menu-button></ha-menu-button><h1 class="grow">Pakkelister</h1>
        <button data-a="template">Skabelon</button>
        <button class="primary" data-a="new-trip">+ Ny tur</button></div>
      ${trips.length ? trips.map(t => `
        <div class="card"><div class="trip" data-a="open-trip" data-id="${t.id}">
          <div class="bar" style="margin:0"><h2 class="grow">${esc(t.name)}</h2>
            <span class="muted">${esc(t.preset || 'Alt')} · ${new Date(t.created).toLocaleDateString('da-DK')}</span></div>
          <div class="muted" style="margin:6px 0">${t.packed} / ${t.total} pakket</div>
          <div class="progress"><div style="width:${t.total ? 100 * t.packed / t.total : 0}%"></div></div>
        </div></div>`).join('') : '<div class="empty">Ingen ture endnu. Opret en ny tur fra skabelonen.</div>'}`;
  }

  // ---------- trip view ----------
  tripView() {
    const { trip, ui } = this;
    const total = trip.items.length, done = trip.items.filter(i => i.packed).length;
    const cats = trip.cats.map(cat => {
      const items = trip.items.filter(i => i.cat === cat);
      const left = items.filter(i => !i.packed).length;
      if (ui.hide && !ui.edit && !left) return '';
      const shown = ui.hide && !ui.edit ? items.filter(i => !i.packed) : items;
      const open = !ui.collapsed[cat];
      return `<div class="card">
        <div class="card-head" data-a="collapse" data-cat="${esc(cat)}" style="cursor:pointer">
          <h2>${esc(cat)}</h2><span class="muted">${items.length - left} / ${items.length}</span><span>${open ? '▾' : '▸'}</span></div>
        ${open ? shown.map(i => ui.edit ? this.editRow(i) : this.packRow(i)).join('') : ''}
        ${open && ui.edit ? `<form class="add" data-form="add-item" data-cat="${esc(cat)}">
          <input type="text" name="n" placeholder="Tilføj ting, fx Shorts (7)" autocomplete="off"><button class="primary">+</button></form>` : ''}
      </div>`;
    }).join('');
    return `
      <div class="sticky">
        <div class="bar"><button class="ghost" data-a="home">‹ Tilbage</button><h1 class="grow">${esc(trip.name)}</h1>
          <button class="${ui.edit ? 'on' : ''}" data-a="edit">${ui.edit ? 'Færdig' : 'Rediger'}</button></div>
        <div class="muted">${done} / ${total} pakket${total && done === total ? ' 🎉' : ''}</div>
        <div class="progress" style="margin:6px 0"><div style="width:${total ? 100 * done / total : 0}%"></div></div>
        ${ui.edit ? '' : `<label style="margin:6px 0"><input type="checkbox" data-a="hide" ${ui.hide ? 'checked' : ''}> Skjul pakkede ting</label>`}
      </div>
      ${cats || '<div class="empty">Intet at vise.</div>'}
      ${ui.edit ? `
        <form class="card add" data-form="add-cat" style="border-top:1px solid var(--line)">
          <input type="text" name="n" placeholder="Ny kategori" autocomplete="off"><button class="primary">+</button></form>
        <div class="bar">
          <button data-a="rename-trip">Omdøb tur</button>
          <button data-a="reset">Fjern alle flueben</button>
          <button class="danger" data-a="delete-trip">Slet tur</button></div>` : ''}`;
  }
  packRow(i) {
    return `<div class="row ${i.packed ? 'packed' : ''}" data-a="toggle" data-id="${i.id}" style="cursor:pointer">
      <span class="check">✓</span><span class="name">${esc(i.name)}</span>${i.qty > 1 ? `<span class="qty">× ${i.qty}</span>` : ''}</div>`;
  }
  editRow(i) {
    return `<div class="row"><span class="name">${esc(i.name)}</span>
      <span class="step"><button data-a="dec" data-id="${i.id}">−</button><span>${i.qty}</span><button data-a="inc" data-id="${i.id}">+</button></span>
      <button class="ghost danger" data-a="del" data-id="${i.id}">✕</button></div>`;
  }

  // ---------- template editor ----------
  saveTemplate() {
    clearTimeout(this._saveTimer);
    this._saveTimer = setTimeout(() => this.api('PUT', 'template', { presets: this.S.presets, template: this.S.template }).catch(e => this.fail(e)), 400);
  }

  templateView() {
    const S = this.S;
    return `
      <div class="bar"><button class="ghost" data-a="home">‹ Tilbage</button><h1 class="grow">Skabelon</h1></div>
      <p class="muted">Her redigerer du den fulde liste. Turtyper bestemmer hvilke ting der kommer med, når du opretter en ny tur. Ændringer gemmes automatisk.</p>
      <div class="card"><div class="card-head"><h2>Turtyper</h2></div>
        ${S.presets.map((p, n) => `<div class="item-edit"><div class="line">
          <input type="text" value="${esc(p)}" data-f="preset" data-n="${n}">
          <button class="ghost danger" data-a="del-preset" data-n="${n}">✕</button></div></div>`).join('')}
        <form class="add" data-form="add-preset"><input type="text" name="n" placeholder="Ny turtype" autocomplete="off"><button class="primary">+</button></form></div>
      ${S.template.map((c, ci) => `
        <div class="card">
          <div class="card-head"><input type="text" value="${esc(c.name)}" data-f="cat" data-ci="${ci}" style="font-weight:600">
            <button data-a="cat-up" data-ci="${ci}">↑</button><button data-a="cat-down" data-ci="${ci}">↓</button>
            <button class="danger" data-a="del-cat" data-ci="${ci}">✕</button></div>
          <div class="item-edit"><div class="muted">Hele kategorien:</div><div class="chips">
            ${S.presets.map((p, pi) => `<button class="chip ${c.items.length && c.items.every(i => i.presets.includes(p)) ? 'on' : ''}" data-a="cat-preset" data-ci="${ci}" data-pi="${pi}">${esc(p)}</button>`).join('')}</div></div>
          ${c.items.map((i, ii) => `<div class="item-edit">
            <div class="line"><input type="text" value="${esc(i.name)}" data-f="item" data-ci="${ci}" data-ii="${ii}">
              <span class="step"><button data-a="t-dec" data-ci="${ci}" data-ii="${ii}">−</button><span>${i.qty}</span><button data-a="t-inc" data-ci="${ci}" data-ii="${ii}">+</button></span>
              <button class="ghost danger" data-a="del-item" data-ci="${ci}" data-ii="${ii}">✕</button></div>
            <div class="chips">${S.presets.map((p, pi) => `<button class="chip ${i.presets.includes(p) ? 'on' : ''}" data-a="item-preset" data-ci="${ci}" data-ii="${ii}" data-pi="${pi}">${esc(p)}</button>`).join('')}</div>
          </div>`).join('')}
          <form class="add" data-form="add-t-item" data-ci="${ci}"><input type="text" name="n" placeholder="Tilføj ting, fx Shorts (7)" autocomplete="off"><button class="primary">+</button></form>
        </div>`).join('')}
      <form class="card add" data-form="add-t-cat"><input type="text" name="n" placeholder="Ny kategori" autocomplete="off"><button class="primary">+</button></form>`;
  }

  // ---------- events ----------
  async tripAction(fn) {
    try { await fn(); } catch (e) { this.fail(e); }
    this.render();
  }

  _bind() {
    const app = this.app;
    app.addEventListener('click', e => this.onClick(e));
    app.addEventListener('change', e => this.onChange(e));
    app.addEventListener('submit', e => this.onSubmit(e));

    const dlg = this.$('new-trip');
    this.$('nt-cancel').onclick = () => dlg.close();
    this.$('new-trip-form').addEventListener('submit', async e => {
      e.preventDefault();
      try {
        const t = await this.api('POST', 'trips', { name: this.$('nt-name').value, preset: this.$('nt-preset').value });
        dlg.close(); this.$('nt-name').value = '';
        this.navigate('trip', t.id);
      } catch (x) { this.fail(x); }
    });
  }

  onClick(e) {
    const el = e.target.closest('[data-a]');
    if (!el) return;
    const { S, ui } = this;
    const trip = this.trip;
    const a = el.dataset.a, id = el.dataset.id;
    const item = id && trip && trip.items.find(i => i.id === id);
    const ci = num(el.dataset.ci), ii = num(el.dataset.ii), pi = num(el.dataset.pi), n = num(el.dataset.n);
    const patch = body => this.api('PATCH', `trips/${trip.id}/items/${id}`, body);
    const reload = async () => { this.trip = await this.api('GET', 'trips/' + trip.id); };
    switch (a) {
      case 'home': this.navigate('list'); break;
      case 'template': this.navigate('template'); break;
      case 'open-trip': this.navigate('trip', id); break;
      case 'new-trip':
        this.$('nt-preset').innerHTML = '<option value="">Alt (hele skabelonen)</option>' + S.presets.map(p => `<option>${esc(p)}</option>`).join('');
        this.$('new-trip').showModal();
        this.$('nt-name').focus();
        break;
      case 'edit': ui.edit = !ui.edit; this.render(); break;
      case 'hide':
        ui.hide = el.checked;
        try { localStorage.setItem('packing_hide', ui.hide ? '1' : '0'); } catch (x) { /* ignore */ }
        this.render(); break;
      case 'collapse': ui.collapsed[el.dataset.cat] = !ui.collapsed[el.dataset.cat]; this.render(); break;
      case 'toggle':
        item.packed = !item.packed; this.render();
        patch({ packed: item.packed }).catch(x => { this.fail(x); this.poll(true); });
        break;
      case 'inc': case 'dec':
        this.tripAction(async () => {
          item.qty = Math.max(1, item.qty + (a === 'inc' ? 1 : -1)); this.render();
          await patch({ qty: item.qty });
        });
        break;
      case 'del':
        if (confirm(`Fjern "${item.name}"?`)) this.tripAction(async () => {
          await this.api('DELETE', `trips/${trip.id}/items/${id}`); await reload();
        });
        break;
      case 'rename-trip': {
        const name = prompt('Nyt navn', trip.name);
        if (name && name.trim()) this.tripAction(async () => { this.trip = await this.api('PATCH', 'trips/' + trip.id, { name }); });
        break;
      }
      case 'reset':
        if (confirm('Fjern alle flueben?')) this.tripAction(async () => { this.trip = await this.api('PATCH', 'trips/' + trip.id, { reset: true }); });
        break;
      case 'delete-trip':
        if (confirm(`Slet turen "${trip.name}"?`)) this.api('DELETE', 'trips/' + trip.id).then(() => this.navigate('list')).catch(x => this.fail(x));
        break;
      // template editor
      case 'cat-up': case 'cat-down': {
        const j = ci + (a === 'cat-up' ? -1 : 1);
        if (j >= 0 && j < S.template.length) { [S.template[ci], S.template[j]] = [S.template[j], S.template[ci]]; this.saveTemplate(); this.render(); }
        break;
      }
      case 'del-cat':
        if (confirm(`Slet kategorien "${S.template[ci].name}" og alle dens ting?`)) { S.template.splice(ci, 1); this.saveTemplate(); this.render(); }
        break;
      case 'del-item': S.template[ci].items.splice(ii, 1); this.saveTemplate(); this.render(); break;
      case 't-inc': case 't-dec': {
        const it = S.template[ci].items[ii]; it.qty = Math.max(1, it.qty + (a === 't-inc' ? 1 : -1)); this.saveTemplate(); this.render(); break;
      }
      case 'item-preset': {
        const it = S.template[ci].items[ii], p = S.presets[pi];
        it.presets = it.presets.includes(p) ? it.presets.filter(x => x !== p) : [...it.presets, p];
        this.saveTemplate(); this.render(); break;
      }
      case 'cat-preset': {
        const items = S.template[ci].items, p = S.presets[pi];
        const all = items.every(i => i.presets.includes(p));
        items.forEach(i => { i.presets = all ? i.presets.filter(x => x !== p) : [...new Set([...i.presets, p])]; });
        this.saveTemplate(); this.render(); break;
      }
      case 'del-preset':
        if (confirm(`Slet turtypen "${S.presets[n]}"?`)) {
          const p = S.presets.splice(n, 1)[0];
          S.template.forEach(c => c.items.forEach(i => { i.presets = i.presets.filter(x => x !== p); }));
          this.saveTemplate(); this.render();
        }
        break;
    }
  }

  // text edits in the template editor
  onChange(e) {
    const f = e.target.dataset.f;
    if (!f) return;
    const S = this.S;
    const v = e.target.value.trim();
    const ci = num(e.target.dataset.ci), ii = num(e.target.dataset.ii), n = num(e.target.dataset.n);
    if (!v) { this.render(); return; }
    if (f === 'cat') S.template[ci].name = v;
    if (f === 'item') {
      const p = parseItem(v), it = S.template[ci].items[ii];
      it.name = p.name;
      if (QTY_RE.test(v)) it.qty = p.qty;
    }
    if (f === 'preset') {
      const old = S.presets[n];
      S.presets[n] = v;
      S.template.forEach(c => c.items.forEach(i => { i.presets = i.presets.map(x => x === old ? v : x); }));
    }
    this.saveTemplate(); this.render();
  }

  onSubmit(e) {
    e.preventDefault();
    const form = e.target, kind = form.dataset.form, input = form.elements.n;
    const v = input.value.trim();
    if (!v) return;
    const { S } = this;
    const ci = num(form.dataset.ci);
    const trip = this.trip;
    const reload = async () => { this.trip = await this.api('GET', 'trips/' + trip.id); };
    if (kind === 'add-item') {
      const p = parseItem(v);
      this.tripAction(async () => { await this.api('POST', `trips/${trip.id}/items`, { cat: form.dataset.cat, ...p }); await reload(); });
    } else if (kind === 'add-cat') {
      this.tripAction(async () => { this.trip = await this.api('PATCH', 'trips/' + trip.id, { add_cat: v }); });
    } else if (kind === 'add-t-item') {
      const p = parseItem(v);
      S.template[ci].items.push({ id: newId(), name: p.name, qty: p.qty, presets: [...S.presets] });
      this.saveTemplate(); this.render();
    } else if (kind === 'add-t-cat') {
      S.template.push({ id: newId(), name: v, items: [] }); this.saveTemplate(); this.render();
    } else if (kind === 'add-preset') {
      if (!S.presets.includes(v)) S.presets.push(v);
      this.saveTemplate(); this.render();
    }
  }

  // keep a trip in sync when several people pack at once
  async poll(force) {
    if (this.nav.view !== 'trip' || !this.trip || !this._started) return;
    if (!force && (this.ui.edit || this.shadowRoot.activeElement?.tagName === 'INPUT')) return;
    try {
      const fresh = await this.api('GET', 'trips/' + this.trip.id);
      if (JSON.stringify(fresh) !== JSON.stringify(this.trip)) { this.trip = fresh; this.render(); }
    } catch (e) { /* transient */ }
  }
}

customElements.define('packing-list-panel', PackingListPanel);
