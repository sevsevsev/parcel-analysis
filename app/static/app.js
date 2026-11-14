/* Land evaluation front end (plain JS, no build step).
 *
 * API endpoints used (contract: docs/API.md, same origin):
 *   GET  /api/geocode?q=<address>        -> {lat, lon, matched, county_fips, county_name, state, supported}
 *   GET  /api/parcel?lat=&lon=           -> {county_fips, parcel_id, label, acres, geometry}
 *   GET  /api/counties                   -> [{fips, name, layers:[{key, description, group, preset[], typical_seconds}]}]
 *   GET  /api/presets                    -> {quick:[keys], build:[...], grow:[...], full:[...]}
 *   POST /api/listings                   -> {listing_id, job_id, url}
 *   GET  /api/jobs/{job_id}              -> {status, step, steps_done, steps_total, log[], error, listing_id}
 *   GET  /api/listings/{id}              -> {listing_id, title, county_fips, parcel_ids, layers, created_at,
 *                                           status, summary|null, files{report, atlas, property_gpkg, ...},
 *                                           parcels_geojson? (optional)}
 *   GET  /api/listings                   -> [listing summary form], newest first (compare)
 *   GET  /api/listings/{id}/report       -> HTML (iframe / new tab)
 *   GET  /api/listings/{id}/atlas.pdf    -> PDF (built on first request, ~10 s)
 *
 * Routing: "/" shows the form; "/listing/<id>" opens the results view for that id.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------- constants
  const IMAGERY_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
  const LABELS_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';
  const IMAGERY_ATTR = 'Esri, Maxar, Earthstar Geographics';
  const POLL_MS = 2000;
  const LOG_LINES = 8;
  const BASE_SECONDS = 15;      // fixed overhead per run
  const SUN_SECONDS = 25;       // added when the elevation layer (dem*) is ticked
  const GROUP_ORDER = ['water', 'soils', 'zoning', 'services', 'context', 'terrain'];
  const PRESET_NAMES = ['quick', 'build', 'grow', 'full'];

  // -------------------------------------------------------------------- state
  const state = {
    map: null,
    marker: null,
    parcelGroup: null,       // L.featureGroup holding the selected parcel polygons
    labelsLayer: null,
    county: null,            // {fips, name, supported}
    parcels: [],             // [{parcel_id, label, acres, geometry, county_fips}]
    highlight: null,         // parcel_id drawn emphasised (hovered or last added)
    counties: [],            // from /api/counties
    presets: {},             // from /api/presets
    catalogError: null,
    preset: 'quick',
    selectedLayers: new Set(),
    lookupBusy: false,       // a parcel lookup is in flight
    job: null,               // {job_id, listing_id, timer}
    listing: null,           // the listing shown in the results view
    view: 'form',            // 'form' | 'running' | 'results'
  };

  // ------------------------------------------------------------------ helpers
  const $ = (id) => document.getElementById(id);

  function showError(id, msg) { $(id).textContent = msg || ''; }
  function clearError(id) { $(id).textContent = ''; }

  function isNum(v) { return typeof v === 'number' && Number.isFinite(v); }
  function fmtAcres(v) { return isNum(v) ? v.toFixed(3) : '—'; }
  function fmtPct(v) { return isNum(v) ? v.toFixed(1) + '%' : '—'; }
  function fmtIndex(v) { return isNum(v) ? v.toFixed(2) : '—'; }
  function fmtDate(s) {
    if (!s) return '—';
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? String(s) : d.toLocaleString();
  }
  function fmtSeconds(s) {
    if (s < 90) return Math.round(s) + ' s';
    const m = Math.floor(s / 60);
    const r = Math.round(s - m * 60);
    return r ? `${m} min ${r} s` : `${m} min`;
  }
  function humanizeStep(step) {
    if (!step) return '';
    const s = String(step).replace(/^\d+[_-]?/, '').replace(/[_-]+/g, ' ').trim();
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
  /* Zoning arrives as a string, a list of strings, or a list of objects with
   * service-specific field names (Code, long_code, ZONE, ...). */
  function fmtZoning(z) {
    if (z == null || z === '') return '—';
    if (typeof z === 'string') return z;
    if (Array.isArray(z)) {
      const parts = z.map(fmtZoning).filter((p) => p && p !== '—');
      return parts.length ? parts.join(', ') : '—';
    }
    if (typeof z === 'object') {
      const keys = ['Code', 'code', 'long_code', 'ZONE', 'zone', 'district', 'District', 'Name', 'name'];
      for (const k of keys) if (typeof z[k] === 'string' && z[k]) return z[k];
      for (const k of Object.keys(z)) if (typeof z[k] === 'string' && z[k]) return z[k];
    }
    return String(z);
  }

  /** fetch wrapper: JSON in/out, throws Error with a short readable message. */
  async function api(path, options) {
    let res;
    try {
      res = await fetch(path, options);
    } catch (err) {
      throw new Error('Could not reach the server.');
    }
    let body = null;
    const text = await res.text();
    if (text) {
      try { body = JSON.parse(text); } catch (e) { body = null; }
    }
    if (!res.ok) {
      const detail = body && (body.detail || body.error || body.message);
      const msg = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : res.statusText || 'Request failed');
      const err = new Error(`${msg} (${res.status})`);
      err.status = res.status;
      throw err;
    }
    return body;
  }

  // ---------------------------------------------------------------------- map
  function initMap() {
    const map = L.map('map', { zoomControl: true, preferCanvas: false }).setView([40.0, -77.0], 6);
    L.tileLayer(IMAGERY_URL, { maxZoom: 19, attribution: IMAGERY_ATTR }).addTo(map);
    state.labelsLayer = L.tileLayer(LABELS_URL, { maxZoom: 19, pane: 'overlayPane', opacity: 0.95 });
    state.parcelGroup = L.featureGroup().addTo(map);
    addLabelsControl(map);
    map.on('click', onMapClick);
    state.map = map;
  }

  function addLabelsControl(map) {
    const Ctl = L.Control.extend({
      options: { position: 'topright' },
      onAdd() {
        const div = L.DomUtil.create('div', 'labels-control leaflet-control');
        div.innerHTML = '<label><input type="checkbox" id="labels-toggle"> Labels</label>';
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        div.querySelector('input').addEventListener('change', (e) => {
          if (e.target.checked) state.labelsLayer.addTo(map); else map.removeLayer(state.labelsLayer);
        });
        return div;
      },
    });
    map.addControl(new Ctl());
  }

  function setMarker(lat, lon) {
    if (state.marker) state.marker.setLatLng([lat, lon]);
    else state.marker = L.marker([lat, lon]).addTo(state.map);
  }

  function onMapClick(e) {
    if (state.view !== 'form') return;
    lookupParcel(e.latlng.lat, e.latlng.lng, { toggle: true });
  }

  function parcelStyle(p) {
    const hi = p.parcel_id === state.highlight;
    return {
      color: '#ffd400',
      weight: hi ? 4 : 2,
      opacity: 1,
      fillColor: '#ffd400',
      fillOpacity: hi ? 0.32 : 0.14,
    };
  }

  function toFeature(p) {
    const g = p.geometry;
    if (!g) return null;
    if (g.type === 'Feature') return g;
    if (g.type === 'FeatureCollection') return g;
    return { type: 'Feature', properties: { parcel_id: p.parcel_id, label: p.label }, geometry: g };
  }

  /** Redraw every selected parcel on the map. */
  function drawParcels() {
    state.parcelGroup.clearLayers();
    for (const p of state.parcels) {
      const feature = toFeature(p);
      if (!feature) continue;
      const layer = L.geoJSON(feature, { style: () => parcelStyle(p) });
      layer.on('click', (ev) => {
        L.DomEvent.stop(ev);           // a click on a drawn parcel removes it without a lookup
        if (state.view === 'form') removeParcel(p.parcel_id);
      });
      layer.on('mouseover', () => setHighlight(p.parcel_id));
      layer.on('mouseout', () => setHighlight(lastParcelId()));
      layer.bindTooltip(`${p.label || p.parcel_id} · ${fmtAcres(p.acres)} ac`, { sticky: true });
      p._layer = layer;
      state.parcelGroup.addLayer(layer);
    }
  }

  function restyleParcels() {
    for (const p of state.parcels) if (p._layer) p._layer.setStyle(parcelStyle(p));
    for (const li of document.querySelectorAll('#parcel-list li')) {
      li.classList.toggle('highlight', li.dataset.id === String(state.highlight));
    }
  }

  function setHighlight(id) {
    if (state.highlight === id) return;
    state.highlight = id;
    restyleParcels();
  }

  function lastParcelId() {
    return state.parcels.length ? state.parcels[state.parcels.length - 1].parcel_id : null;
  }

  function fitTo(layer, force) {
    if (!layer) return;
    const b = layer.getBounds();
    if (!b || !b.isValid()) return;
    if (force || !state.map.getBounds().contains(b)) {
      state.map.fitBounds(b.pad(0.4), { maxZoom: 18 });
    }
  }

  // ------------------------------------------------------------------ geocode
  async function onGeocodeSubmit(ev) {
    ev.preventDefault();
    const q = $('address').value.trim();
    clearError('geocode-error');
    if (!q) { showError('geocode-error', 'Type an address first.'); return; }
    const btn = $('find-btn');
    btn.disabled = true;
    $('geocode-result').textContent = 'Searching…';
    try {
      const r = await api(`/api/geocode?q=${encodeURIComponent(q)}`);
      const lat = Number(r.lat), lon = Number(r.lon);
      setMarker(lat, lon);
      state.map.flyTo([lat, lon], 17, { duration: 1.2 });
      const name = r.county_name ? `${r.county_name}${r.state ? ', ' + r.state : ''}` : 'unknown county';
      $('geocode-result').innerHTML = `<strong>${escapeHtml(r.matched || q)}</strong><br><span class="muted">${escapeHtml(name)}</span>`;
      setCounty({ fips: r.county_fips, name: r.county_name || r.county_fips, supported: r.supported !== false });
      if (r.supported !== false) {
        await lookupParcel(lat, lon, { toggle: false, address: r.matched });
      }
    } catch (err) {
      $('geocode-result').textContent = '';
      showError('geocode-error', err.status === 404 ? 'No match for that address.' : err.message);
    } finally {
      btn.disabled = false;
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  // ------------------------------------------------------------------- county
  function countyRecord(fips) {
    return state.counties.find((c) => String(c.fips) === String(fips)) || null;
  }

  function setCounty(c) {
    if (!c || !c.fips) return;
    const rec = countyRecord(c.fips);
    state.county = {
      fips: c.fips,
      name: c.name || (rec && rec.name) || c.fips,
      supported: c.supported !== false,
    };
    const note = $('county-note');
    if (!state.county.supported) {
      note.textContent = `Parcel lookup is not available for ${state.county.name}. Clicking the map still works for national layers only; running an evaluation there is not supported yet.`;
      note.hidden = false;
    } else {
      note.hidden = true;
      note.textContent = '';
    }
    renderLayers();
    updateRunState();
  }

  // ------------------------------------------------------------------ parcels
  async function lookupParcel(lat, lon, { toggle, address }) {
    if (state.lookupBusy) return;
    state.lookupBusy = true;
    clearError('parcel-error');
    try {
      // after a geocode: search the parcel service by the matched address first (the geocoded
      // point is interpolated along the street and can land on a neighbour); map clicks must
      // hit a parcel exactly, so no nearest-parcel fallback for them
      let url = `/api/parcel?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;
      if (address) url += `&address=${encodeURIComponent(address)}`;
      if (toggle) url += '&nearest=0';
      const p = await api(url);
      if (!p || !p.parcel_id) throw new Error('No parcel returned.');
      const existing = state.parcels.find((x) => x.parcel_id === p.parcel_id);
      if (existing && toggle) removeParcel(p.parcel_id);
      else addParcel(p, { fit: !toggle });   // geocoded parcel: bring it into view; clicked: leave the map alone
    } catch (err) {
      if (err.status === 404) {
        showError('parcel-error', state.county && !state.county.supported
          ? `No parcel service for ${state.county.name}.`
          : 'No parcel found at that point.');
      } else {
        showError('parcel-error', err.message);
      }
    } finally {
      state.lookupBusy = false;
    }
  }

  function addParcel(p, { fit } = {}) {
    const existing = state.parcels.find((x) => x.parcel_id === p.parcel_id);
    if (existing) { setHighlight(p.parcel_id); return; }
    if (state.parcels.length && p.county_fips && state.parcels[0].county_fips && String(p.county_fips) !== String(state.parcels[0].county_fips)) {
      showError('parcel-error', 'All parcels in one evaluation must be in the same county. Clear the selection to start in another county.');
      return;
    }
    state.parcels.push({
      parcel_id: p.parcel_id,
      label: p.label || p.parcel_id,
      acres: Number(p.acres),
      geometry: p.geometry,
      county_fips: p.county_fips,
    });
    if (!state.county || String(state.county.fips) !== String(p.county_fips)) {
      if (p.county_fips) setCounty({ fips: p.county_fips, supported: true });
    }
    state.highlight = p.parcel_id;
    drawParcels();
    renderParcelList();
    updateRunState();
    if (fit) fitTo(state.parcels[state.parcels.length - 1]._layer, true);
  }

  function removeParcel(id) {
    state.parcels = state.parcels.filter((x) => x.parcel_id !== id);
    state.highlight = lastParcelId();
    drawParcels();
    renderParcelList();
    updateRunState();
  }

  function clearParcels() {
    state.parcels = [];
    state.highlight = null;
    drawParcels();
    renderParcelList();
    updateRunState();
    clearError('parcel-error');
  }

  function renderParcelList() {
    const ul = $('parcel-list');
    ul.innerHTML = '';
    for (const p of state.parcels) {
      const li = document.createElement('li');
      li.dataset.id = p.parcel_id;
      if (p.parcel_id === state.highlight) li.classList.add('highlight');
      const label = document.createElement('span');
      label.className = 'plabel';
      label.textContent = p.label;
      label.title = p.label;
      const acres = document.createElement('span');
      acres.className = 'pacres';
      acres.textContent = isNum(p.acres) ? `${fmtAcres(p.acres)} ac` : '';
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'remove-btn';
      btn.setAttribute('aria-label', `Remove ${p.label}`);
      btn.textContent = '×';
      btn.addEventListener('click', (e) => { e.stopPropagation(); removeParcel(p.parcel_id); });
      li.append(label, acres, btn);
      li.addEventListener('mouseenter', () => setHighlight(p.parcel_id));
      li.addEventListener('mouseleave', () => setHighlight(lastParcelId()));
      li.addEventListener('click', () => { setHighlight(p.parcel_id); fitTo(p._layer, true); });
      ul.appendChild(li);
    }
    const total = state.parcels.reduce((s, p) => s + (isNum(p.acres) ? p.acres : 0), 0);
    $('parcel-total').textContent = state.parcels.length
      ? `${state.parcels.length} parcel${state.parcels.length === 1 ? '' : 's'} · ${fmtAcres(total)} acres (sum of parcel records)`
      : '';
    $('clear-parcels').disabled = state.parcels.length === 0;
  }

  // ------------------------------------------------------------------- layers
  async function loadCatalog() {
    const results = await Promise.allSettled([api('/api/counties'), api('/api/presets')]);
    const [cRes, pRes] = results;
    if (cRes.status === 'fulfilled' && Array.isArray(cRes.value)) state.counties = cRes.value;
    if (pRes.status === 'fulfilled' && pRes.value && typeof pRes.value === 'object') state.presets = pRes.value;
    const failed = results.filter((r) => r.status === 'rejected');
    state.catalogError = failed.length ? `Layer catalog unavailable: ${failed[0].reason.message}` : null;
    if (state.catalogError) showError('layers-error', state.catalogError);
    // the county may already be known (geocode raced the catalog)
    if (state.county) {
      state.county.name = state.county.name || (countyRecord(state.county.fips) || {}).name || state.county.fips;
      renderLayers();
    }
  }

  function countyLayers() {
    const rec = state.county ? countyRecord(state.county.fips) : null;
    return rec && Array.isArray(rec.layers) ? rec.layers : [];
  }

  function layerInPreset(layer, preset) {
    if (Array.isArray(layer.preset) && layer.preset.includes(preset)) return true;
    const keys = state.presets[preset];
    return Array.isArray(keys) && keys.includes(layer.key);
  }

  function renderLayers() {
    const container = $('layer-groups');
    const presets = $('presets');
    container.innerHTML = '';
    if (!state.county) {
      presets.hidden = true;
      container.innerHTML = '<p class="hint">Find an address or click a parcel to see the layers available in that county.</p>';
      updateEstimate();
      return;
    }
    const layers = countyLayers();
    if (!layers.length) {
      presets.hidden = true;
      container.innerHTML = `<p class="hint">${state.catalogError ? 'The layer catalog could not be loaded.' : `No layer catalog for ${escapeHtml(state.county.name)}.`}</p>`;
      updateEstimate();
      return;
    }
    presets.hidden = false;
    // keep existing ticks when re-rendering for the same county; otherwise apply the preset
    const known = new Set(layers.map((l) => l.key));
    const keep = [...state.selectedLayers].filter((k) => known.has(k));
    if (keep.length) state.selectedLayers = new Set(keep);
    else state.selectedLayers = new Set(layers.filter((l) => layerInPreset(l, state.preset)).map((l) => l.key));

    const groups = new Map();
    for (const l of layers) {
      const g = l.group || 'other';
      if (!groups.has(g)) groups.set(g, []);
      groups.get(g).push(l);
    }
    const order = [...groups.keys()].sort((a, b) => {
      const ia = GROUP_ORDER.indexOf(a), ib = GROUP_ORDER.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
    for (const g of order) {
      const div = document.createElement('div');
      div.className = 'layer-group';
      const h = document.createElement('h4');
      h.textContent = g;
      div.appendChild(h);
      for (const l of groups.get(g)) {
        const label = document.createElement('label');
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = l.key;
        cb.dataset.layer = l.key;
        cb.checked = state.selectedLayers.has(l.key);
        cb.addEventListener('change', () => {
          if (cb.checked) state.selectedLayers.add(l.key); else state.selectedLayers.delete(l.key);
          updateEstimate();
        });
        const desc = document.createElement('span');
        desc.className = 'ldesc';
        desc.textContent = l.description || l.key;
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.textContent = isNum(l.typical_seconds) ? `~${l.typical_seconds} s` : '';
        tag.title = 'Typical fetch time';
        label.append(cb, desc, tag);
        div.appendChild(label);
      }
      container.appendChild(div);
    }
    updateEstimate();
  }

  function applyPreset(name) {
    state.preset = name;
    const layers = countyLayers();
    state.selectedLayers = new Set(layers.filter((l) => layerInPreset(l, name)).map((l) => l.key));
    for (const cb of document.querySelectorAll('#layer-groups input[type=checkbox]')) {
      cb.checked = state.selectedLayers.has(cb.dataset.layer);
    }
    updateEstimate();
  }

  function updateEstimate() {
    const el = $('estimate');
    const layers = countyLayers();
    if (!layers.length) { el.textContent = ''; return; }
    let secs = BASE_SECONDS;
    let sun = false;
    for (const l of layers) {
      if (!state.selectedLayers.has(l.key)) continue;
      secs += isNum(l.typical_seconds) ? l.typical_seconds : 0;
      if (String(l.key).startsWith('dem')) sun = true;
    }
    if (sun) secs += SUN_SECONDS;
    el.textContent = `${state.selectedLayers.size} layer${state.selectedLayers.size === 1 ? '' : 's'} · estimated run time about ${fmtSeconds(secs)}${sun ? ' (includes the sun model)' : ''}`;
  }

  // ---------------------------------------------------------------------- run
  function updateRunState() {
    const btn = $('run-btn');
    const note = $('run-note');
    let reason = '';
    if (state.job) reason = 'An evaluation is already running.';
    else if (!state.parcels.length) reason = 'Select at least one parcel to run.';
    else if (!state.county) reason = 'County unknown; find an address first.';
    else if (!state.county.supported) reason = `Evaluations are not available for ${state.county.name} yet.`;
    btn.disabled = Boolean(reason);
    note.textContent = reason;
  }

  function readThresholds() {
    const out = {};
    for (const input of document.querySelectorAll('[data-threshold]')) {
      const v = parseFloat(input.value);
      if (Number.isFinite(v)) out[input.dataset.threshold] = v;
    }
    return out;
  }

  async function onRun() {
    clearError('run-error');
    if ($('run-btn').disabled) return;
    const fips = state.county.fips || state.parcels[0].county_fips;
    const body = {
      county_fips: fips,
      parcel_ids: state.parcels.map((p) => p.parcel_id),
      layers: [...state.selectedLayers],
      thresholds: readThresholds(),
      pdf: $('opt-pdf').checked,
    };
    const title = $('title').value.trim();
    if (title) body.title = title;
    $('run-btn').disabled = true;
    try {
      const r = await api('/api/listings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      state.job = { job_id: r.job_id, listing_id: r.listing_id, timer: null };
      $('running-title').textContent = title || `Listing ${r.listing_id}`;
      resetProgress();
      setView('running');
      startPolling();
    } catch (err) {
      showError('run-error', err.message);
    }
    updateRunState();
  }

  function resetProgress() {
    $('progress-bar').style.width = '0%';
    $('progress').setAttribute('aria-valuenow', '0');
    $('progress-step').textContent = 'Queued';
    $('progress-log').textContent = '';
    clearError('running-error');
    $('running-back').hidden = true;
  }

  function startPolling() {
    stopPolling();
    pollJob();
    state.job.timer = setInterval(pollJob, POLL_MS);
  }

  function stopPolling() {
    if (state.job && state.job.timer) clearInterval(state.job.timer);
    if (state.job) state.job.timer = null;
  }

  async function pollJob() {
    if (!state.job) return;
    const job = state.job;
    try {
      if (job.job_id) {
        const j = await api(`/api/jobs/${encodeURIComponent(job.job_id)}`);
        renderProgress(j);
        if (j.listing_id) job.listing_id = j.listing_id;
        if (j.status === 'done') finishJob(job.listing_id);
        else if (j.status === 'failed') failJob(j.error || 'The evaluation failed.');
      } else {
        // No job id known (listing opened by URL while running): poll the listing itself.
        const l = await api(`/api/listings/${encodeURIComponent(job.listing_id)}`);
        renderProgress({ status: l.status, step: l.status });
        if (l.status === 'done') finishJob(job.listing_id);
        else if (l.status === 'failed') failJob(l.error || 'The evaluation failed.');
      }
    } catch (err) {
      // transient: keep polling, but say so
      showError('running-error', `Progress check failed: ${err.message}. Retrying…`);
    }
  }

  function renderProgress(j) {
    clearError('running-error');
    const total = isNum(j.steps_total) && j.steps_total > 0 ? j.steps_total : 0;
    const done = isNum(j.steps_done) ? j.steps_done : 0;
    const pct = total ? Math.max(0, Math.min(100, Math.round((done / total) * 100))) : (j.status === 'done' ? 100 : 0);
    $('progress-bar').style.width = pct + '%';
    $('progress').setAttribute('aria-valuenow', String(pct));
    const stepText = j.step ? humanizeStep(j.step) : (j.status === 'queued' ? 'Queued' : 'Starting');
    $('progress-step').textContent = total ? `${stepText} · step ${Math.min(done + 1, total)} of ${total}` : stepText;
    if (Array.isArray(j.log) && j.log.length) {
      const pre = $('progress-log');
      pre.textContent = j.log.slice(-LOG_LINES).join('\n');
      pre.scrollTop = pre.scrollHeight;
    }
  }

  async function finishJob(listingId) {
    stopPolling();
    state.job = null;
    updateRunState();
    $('progress-bar').style.width = '100%';
    try {
      await loadListing(listingId);
    } catch (err) {
      showError('running-error', err.message);
      $('running-back').hidden = false;
    }
  }

  function failJob(msg) {
    stopPolling();
    state.job = null;
    updateRunState();
    $('progress-step').textContent = 'Failed';
    showError('running-error', msg);
    $('running-back').hidden = false;
  }

  // ------------------------------------------------------------------ results
  async function loadListing(id) {
    const l = await api(`/api/listings/${encodeURIComponent(id)}`);
    if (!l || !l.listing_id) l.listing_id = id;
    if (l.status === 'running' || l.status === 'queued') {
      state.job = { job_id: l.job_id || null, listing_id: l.listing_id, timer: null };
      $('running-title').textContent = l.title || `Listing ${l.listing_id}`;
      resetProgress();
      setView('running');
      updateRunState();
      startPolling();
      return;
    }
    showResults(l);
  }

  function showResults(l) {
    state.listing = l;
    const id = l.listing_id;
    const files = l.files || {};
    $('results-heading').textContent = l.title || `Listing ${id}`;
    const meta = [];
    if (l.created_at) meta.push(fmtDate(l.created_at));
    if (Array.isArray(l.parcel_ids)) meta.push(`${l.parcel_ids.length} parcel${l.parcel_ids.length === 1 ? '' : 's'}`);
    if (l.status && l.status !== 'done') meta.push(`status: ${l.status}`);
    $('results-meta').textContent = meta.join(' · ');
    clearError('results-error');
    if (l.status === 'failed') showError('results-error', l.error || 'This evaluation failed.');
    else if (!l.summary) showError('results-error', 'No summary is available for this listing yet.');

    renderSummary(l.summary || {});

    const reportUrl = files.report || `/api/listings/${encodeURIComponent(id)}/report`;
    const atlasUrl = files.atlas || `/api/listings/${encodeURIComponent(id)}/atlas.pdf`;
    $('link-report').href = reportUrl;
    $('link-atlas').href = atlasUrl;
    setDownload($('link-property'), files.property_gpkg);
    setDownload($('link-evaluation'), files.evaluation_gpkg);
    const frame = $('report-frame');
    if (l.status === 'done' || l.summary) { frame.src = reportUrl; frame.hidden = false; }
    else { frame.removeAttribute('src'); frame.hidden = true; }

    const shareUrl = `${location.origin}/listing/${encodeURIComponent(id)}`;
    $('share-url').value = shareUrl;
    $('copy-status').textContent = '';
    if (location.pathname !== `/listing/${id}`) {
      try { history.pushState({ listing: id }, '', `/listing/${encodeURIComponent(id)}`); } catch (e) { /* file:// etc. */ }
    }
    if (l.parcels_geojson) drawListingParcels(l.parcels_geojson);
    setView('results');
  }

  function setDownload(a, url) {
    if (url) { a.href = url; a.hidden = false; } else { a.hidden = true; a.removeAttribute('href'); }
  }

  function renderSummary(s) {
    const cards = [
      { label: 'Property', value: fmtAcres(s.property_acres), sub: 'acres, dissolved boundary' },
      { label: 'Buildable', value: fmtAcres(s.buildable_acres), sub: isNum(s.buildable_pct) ? `acres · ${fmtPct(s.buildable_pct)}` : 'acres' },
      { label: 'Garden grade', value: fmtAcres(s.garden_acres), sub: 'acres, no setback' },
      { label: 'Usable', value: fmtPct(s.usable_pct), sub: 'build, grow or graze' },
      { label: 'Winter solar index', value: fmtIndex(s.dec21_solar_index_buildable), sub: 'Dec 21, buildable ground; 1 = flat open' },
      { label: 'Run-on', value: fmtAcres(s.runon_acres), sub: 'off-site acres draining in' },
      { label: 'Historic', value: fmtPct(s.historic_pct), sub: 'of property in a district' },
      { label: 'Zoning', value: fmtZoning(s.zoning), sub: '', wide: true },
    ];
    const el = $('summary-cards');
    el.innerHTML = '';
    for (const c of cards) {
      const d = document.createElement('div');
      d.className = 'card' + (c.wide ? ' wide' : '');
      const v = document.createElement('div');
      v.className = 'cval';
      v.textContent = c.value;
      const lab = document.createElement('div');
      lab.className = 'clabel';
      lab.textContent = c.label;
      d.append(v, lab);
      if (c.sub) {
        const sub = document.createElement('div');
        sub.className = 'csub';
        sub.textContent = c.sub;
        d.appendChild(sub);
      }
      el.appendChild(d);
    }
  }

  function drawListingParcels(geojson) {
    try {
      state.parcelGroup.clearLayers();
      state.parcels = [];
      state.highlight = null;
      renderParcelList();
      const layer = L.geoJSON(geojson, { style: () => ({ color: '#ffd400', weight: 2, fillColor: '#ffd400', fillOpacity: 0.14 }) });
      state.parcelGroup.addLayer(layer);
      fitTo(layer, true);
    } catch (err) {
      showError('results-error', `Could not draw the parcels: ${err.message}`);
    }
  }

  async function copyShare() {
    const input = $('share-url');
    const status = $('copy-status');
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(input.value);
      else { input.select(); document.execCommand('copy'); }
      status.textContent = 'Copied.';
    } catch (e) {
      input.select();
      status.textContent = 'Press Ctrl+C to copy.';
    }
    setTimeout(() => { status.textContent = ''; }, 2500);
  }

  function onNewEvaluation() {
    state.listing = null;
    $('report-frame').removeAttribute('src');
    try { history.pushState({}, '', '/'); } catch (e) { /* ignore */ }
    setView('form');
    updateRunState();
  }

  // ------------------------------------------------------------------ compare
  async function openCompare() {
    const dlg = $('compare-dialog');
    clearError('compare-error');
    $('compare-body').innerHTML = '<tr><td colspan="7" class="muted">Loading…</td></tr>';
    if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
    try {
      const list = await api('/api/listings');
      renderCompare(Array.isArray(list) ? list : []);
    } catch (err) {
      $('compare-body').innerHTML = '';
      showError('compare-error', err.message);
    }
  }

  function renderCompare(list) {
    const tbody = $('compare-body');
    tbody.innerHTML = '';
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted">No listings yet.</td></tr>';
      return;
    }
    for (const l of list) {
      const s = l.summary || {};
      const tr = document.createElement('tr');
      const tdTitle = document.createElement('td');
      const a = document.createElement('a');
      a.href = `/listing/${encodeURIComponent(l.listing_id)}`;
      a.textContent = l.title || `Listing ${l.listing_id}`;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        closeCompare();
        loadListing(l.listing_id).catch((err) => showError('results-error', err.message));
      });
      tdTitle.appendChild(a);
      if (l.status && l.status !== 'done') {
        const st = document.createElement('span');
        st.className = 'muted';
        st.textContent = ` (${l.status})`;
        tdTitle.appendChild(st);
      }
      tr.appendChild(tdTitle);
      for (const v of [fmtAcres(s.property_acres), fmtPct(s.buildable_pct), fmtAcres(s.garden_acres), fmtPct(s.usable_pct), fmtIndex(s.dec21_solar_index_buildable)]) {
        const td = document.createElement('td');
        td.className = 'num';
        td.textContent = v;
        tr.appendChild(td);
      }
      const tdDate = document.createElement('td');
      tdDate.textContent = fmtDate(l.created_at);
      tr.appendChild(tdDate);
      tbody.appendChild(tr);
    }
  }

  function closeCompare() {
    const dlg = $('compare-dialog');
    if (dlg.open) dlg.close(); else dlg.removeAttribute('open');
  }

  // --------------------------------------------------------------------- views
  function setView(name) {
    state.view = name;
    $('view-form').hidden = name !== 'form';
    $('view-running').hidden = name !== 'running';
    $('view-results').hidden = name !== 'results';
    $('panel-body').scrollTop = 0;
    const panel = $('panel');
    if (panel.classList.contains('collapsed')) toggleSheet(false);
    setTimeout(() => state.map && state.map.invalidateSize(), 50);
  }

  function toggleSheet(collapse) {
    const panel = $('panel');
    const collapsed = typeof collapse === 'boolean' ? collapse : !panel.classList.contains('collapsed');
    panel.classList.toggle('collapsed', collapsed);
    const btn = $('sheet-toggle');
    btn.setAttribute('aria-expanded', String(!collapsed));
    btn.setAttribute('aria-label', collapsed ? 'Expand panel' : 'Collapse panel');
  }

  // --------------------------------------------------------------------- init
  function wireEvents() {
    $('geocode-form').addEventListener('submit', onGeocodeSubmit);
    $('clear-parcels').addEventListener('click', clearParcels);
    for (const r of document.querySelectorAll('input[name=preset]')) {
      r.addEventListener('change', () => { if (r.checked) applyPreset(r.value); });
    }
    $('run-btn').addEventListener('click', onRun);
    $('running-back').addEventListener('click', () => { setView('form'); updateRunState(); });
    $('new-eval').addEventListener('click', onNewEvaluation);
    $('copy-share').addEventListener('click', copyShare);
    $('compare-btn').addEventListener('click', openCompare);
    $('compare-close').addEventListener('click', closeCompare);
    $('sheet-toggle').addEventListener('click', (e) => { e.stopPropagation(); toggleSheet(); });
    document.querySelector('.panel-header').addEventListener('click', (e) => {
      if (window.matchMedia('(max-width: 799px)').matches && !e.target.closest('button')) toggleSheet();
    });
    window.addEventListener('popstate', () => {
      const id = listingIdFromPath();
      if (id) loadListing(id).catch((err) => showError('results-error', err.message));
      else if (state.view === 'results') { setView('form'); updateRunState(); }
    });
    window.addEventListener('resize', () => state.map && state.map.invalidateSize());
  }

  function listingIdFromPath() {
    const m = location.pathname.match(/^\/listing\/([^/]+)\/?$/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  async function init() {
    initMap();
    wireEvents();
    renderParcelList();
    updateRunState();
    const catalog = loadCatalog();
    const id = listingIdFromPath();
    if (id) {
      setView('results');
      $('results-heading').textContent = `Listing ${id}`;
      $('results-meta').textContent = 'Loading…';
      try {
        await loadListing(id);
      } catch (err) {
        $('results-meta').textContent = '';
        showError('results-error', `Could not load listing ${id}: ${err.message}`);
      }
    }
    await catalog;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
