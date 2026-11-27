
'use strict';

const DATA_URL = 'data/datos_resumen.json';
const GEO_URL = 'data/malaga.geojson';

const state = {
  data: [], geojson: null, map: null, geoLayer: null, mapLoading: false,
  view: 'resumen',
  summaryPeriod: '', cp: '29001', cpPeriod: '',
  summaryMetric: 'importe_medio',
  cpMetric: 'importe_medio',
  mapMetric: 'importe_medio'
};

const $ = id => document.getElementById(id);
const numberFormat = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0 });
const currencyFormat = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0
});

const metricConfig = {
  precio_m2: {
    label: 'Precio medio por m²',
    subtitle: 'Serie mensual · euros por metro cuadrado',
    format: value => `${numberFormat.format(value)} €/m²`
  },
  compraventas: {
    label: 'Compraventas',
    subtitle: 'Serie mensual · número de operaciones',
    format: value => numberFormat.format(value)
  },
  importe_medio: {
    label: 'Importe medio',
    subtitle: 'Serie mensual · euros por operación',
    format: value => currencyFormat.format(value)
  }
};

function rowsForCP(cp = state.cp) {
  return state.data
    .filter(row => row.tipo_ambito === 'cp' && String(row.cp) === String(cp))
    .sort((a, b) => a.periodo.localeCompare(b.periodo));
}

function provincialRows() {
  return state.data
    .filter(row =>
      row.tipo_ambito === 'provincia' &&
      row.municipio === 'Málaga' &&
      row.cp === 'Todos'
    )
    .sort((a, b) => a.periodo.localeCompare(b.periodo));
}

function numeric(rows, key) {
  return rows.map(row => row[key]).filter(value =>
    typeof value === 'number' && Number.isFinite(value)
  );
}

function average(rows, key) {
  const values = numeric(rows, key);
  return values.length
    ? values.reduce((a, b) => a + b, 0) / values.length
    : null;
}

function total(rows, key) {
  const values = numeric(rows, key);
  return values.length
    ? values.reduce((a, b) => a + b, 0)
    : null;
}

function fmtPrice(value) {
  return value === null ? 'Sin datos' : `${numberFormat.format(value)} €/m²`;
}

function fmtMoney(value) {
  return value === null ? 'Sin datos' : currencyFormat.format(value);
}

function fmtNumber(value) {
  return value === null ? 'Sin datos' : numberFormat.format(value);
}

function formatPeriod(period) {
  if (!period) return 'Sin datos';

  const [year, month] = period.split('-').map(Number);

  return new Intl.DateTimeFormat('es-ES', {
    month: 'long',
    year: 'numeric'
  }).format(new Date(year, month - 1, 1));
}

function shortPeriod(period) {
  if (!period) return 'Sin datos';

  const [year, month] = period.split('-');

  return `${
    ['Ene.', 'Feb.', 'Mar.', 'Abr.', 'May.', 'Jun.',
     'Jul.', 'Ago.', 'Sep.', 'Oct.', 'Nov.', 'Dic.'][Number(month) - 1]
  } ${year}`;
}

function selectedRows(rows, period) {
  return rows.filter(row => row.periodo === period);
}

function availablePeriods(rows) {
  return [...new Set(rows.map(row => row.periodo))].sort().reverse();
}

function setupPicker({
  rootId,
  triggerId,
  menuId,
  chipId,
  getOptions,
  getSelected,
  setSelected,
  onChange
}) {
  const root = $(rootId);
  const trigger = $(triggerId);
  const menu = $(menuId);
  const chip = $(chipId);

  if (!root || !trigger || !menu || !chip) return;

  const refresh = () => {
    const options = getOptions();
    const selected = getSelected();

    chip.textContent = root.classList.contains('cp-picker')
      ? selected
      : shortPeriod(selected);

    menu.replaceChildren();

    options.forEach(value => {
      const button = document.createElement('button');

      button.type = 'button';
      button.className = `period-option${value === selected ? ' selected' : ''}`;

      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', String(value === selected));

      button.textContent = root.classList.contains('cp-picker')
        ? value
        : shortPeriod(value);

      button.addEventListener('click', () => {
        setSelected(value);

        root.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');

        refresh();
        onChange();
      });

      menu.appendChild(button);
    });
  };

  trigger.addEventListener('click', () => {
    const open = root.classList.toggle('open');
    trigger.setAttribute('aria-expanded', String(open));
  });

  document.addEventListener('click', event => {
    if (!root.contains(event.target)) {
      root.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
    }
  });

  refresh();

  return refresh;
}

function setupPickers() {
  setupPicker({
    rootId: 'period-picker-resumen',
    triggerId: 'period-trigger-resumen',
    menuId: 'period-menu-resumen',
    chipId: 'period-chip-resumen',

    getOptions: () => availablePeriods(provincialRows()),
    getSelected: () => state.summaryPeriod,
    setSelected: value => state.summaryPeriod = value,

    onChange: renderSummary
  });

  setupPicker({
    rootId: 'cp-picker',
    triggerId: 'cp-trigger',
    menuId: 'cp-menu',
    chipId: 'cp-chip',

    getOptions: () => [
      ...new Set(
        state.data
          .filter(row => row.tipo_ambito === 'cp')
          .map(row => String(row.cp))
      )
    ].sort(),

    getSelected: () => state.cp,

    setSelected: value => {
      state.cp = value;

      const periods = availablePeriods(rowsForCP());
      state.cpPeriod = periods[0] || '';

      refreshCPPeriod();
    },

    onChange: renderPostal
  });

  refreshCPPeriod = setupPicker({
    rootId: 'period-picker-codigos',
    triggerId: 'period-trigger-codigos',
    menuId: 'period-menu-codigos',
    chipId: 'period-chip-codigos',

    getOptions: () => availablePeriods(rowsForCP()),
    getSelected: () => state.cpPeriod,
    setSelected: value => state.cpPeriod = value,

    onChange: renderPostal
  });
}

let refreshCPPeriod = () => {};

function setupMetricButtons(selector, stateKey, renderFn) {
  document.querySelectorAll(selector).forEach(button => {
    button.addEventListener('click', () => {
      state[stateKey] =
        button.dataset.metric ||
        button.dataset.cpMetric ||
        button.dataset.mapMetric;

      document.querySelectorAll(selector).forEach(item => {
        const active =
          (item.dataset.metric ||
           item.dataset.cpMetric ||
           item.dataset.mapMetric) === state[stateKey];

        item.classList.toggle('active', active);
        item.setAttribute('aria-pressed', String(active));
      });

      renderFn();
    });
  });
}

function setupNavigation() {
  document.querySelectorAll('[data-view]').forEach(button => {
    button.addEventListener('click', () => activateView(button.dataset.view));
  });

  document.querySelectorAll('[data-go]').forEach(button => {
    button.addEventListener('click', () => activateView(button.dataset.go));
  });
}

function activateView(name) {
  state.view = name;

  document.querySelector('.main-area').dataset.currentView = name;

  document.querySelectorAll('.view').forEach(view => {
    view.classList.toggle('active', view.id === `view-${name}`);
  });

  document.querySelectorAll('.nav-link').forEach(button => {
    button.classList.toggle('active', button.dataset.view === name);
  });

  if (name === 'codigos') {
    if (!state.map && !state.mapLoading) {
      setTimeout(() => {
        initMap().catch(error => {
          state.mapLoading = false;
          console.error('Error al cargar el mapa:', error);

          showEmpty(
            $('postal-map'),
            `No se ha podido cargar el mapa: ${error.message}`
          );
        });
      }, 100);

    } else if (state.map) {
      setTimeout(() => {
        state.map.invalidateSize();

        const bounds = L.geoJSON(state.geojson).getBounds();

        if (bounds.isValid()) {
          state.map.fitBounds(bounds, { padding: [8, 8] });
        }
      }, 100);
    }
  }
}

function centeredAverage(series) {
  if (series.length < 3) return [];

  return series.slice(1, -1).flatMap((point, index) => {
    const values = [
      series[index].value,
      point.value,
      series[index + 2].value
    ];

    return values.every(value =>
      typeof value === 'number' && Number.isFinite(value)
    )
      ? [{
          label: point.label,
          value: values.reduce((a, b) => a + b, 0) / 3
        }]
      : [];
  });
}

function monthlySeries(rows, key) {
  if (!rows.length) return [];

  const byPeriod = new Map(rows.map(row => [row.periodo, row[key]]));

  const [startYear, startMonth] = rows[0].periodo.split('-').map(Number);
  const [endYear, endMonth] = rows[rows.length - 1].periodo.split('-').map(Number);

  const start = startYear * 12 + startMonth - 1;
  const end = endYear * 12 + endMonth - 1;

  const result = [];

  for (let n = start; n <= end; n++) {
    const year = Math.floor(n / 12);
    const month = n % 12 + 1;

    const period = `${year}-${String(month).padStart(2, '0')}`;
    const value = byPeriod.get(period);

    result.push({
      label: period,
      value: typeof value === 'number' && Number.isFinite(value)
        ? value
        : null
    });
  }

  return result;
}

function drawLine(element, series, metric, trend = []) {
  if (!element) return;

  if (
    !series.length ||
    !series.some(item => typeof item.value === 'number')
  ) {
    showEmpty(element, 'No hay valores disponibles para esta selección.');
    return;
  }

  const width = 760;
  const height = 330;

  const margin = {
    left: 58,
    right: 18,
    top: 18,
    bottom: 42
  };

  const valid = series.filter(item =>
    typeof item.value === 'number' && Number.isFinite(item.value)
  );

  const max = Math.max(...valid.map(item => item.value), 1);
  const high = max * 1.1;

  const x = i =>
    margin.left +
    (series.length === 1
      ? 0
      : i * (width - margin.left - margin.right) / (series.length - 1));

  const y = v =>
    height - margin.bottom -
    v / high * (height - margin.top - margin.bottom);

  const ticks = [0, 1, 2, 3].map(i => {
    const value = high * i / 3;
    const yy = y(value);

    return `
      <line class="chart-grid"
        x1="${margin.left}" y1="${yy}"
        x2="${width - margin.right}" y2="${yy}"/>
      <text class="chart-label"
        x="${margin.left - 9}" y="${yy + 3}"
        text-anchor="end">${numberFormat.format(value)}</text>
    `;
  }).join('');

  const labels = series.map((item, i) => {
    if (
      series.length > 8 &&
      i % Math.ceil(series.length / 7) !== 0 &&
      i !== series.length - 1
    ) {
      return '';
    }

    return `
      <text class="chart-label"
        x="${x(i)}" y="${height - 10}"
        text-anchor="middle">
        ${escapeHtml(shortPeriod(item.label))}
      </text>
    `;
  }).join('');

  const segments = [];
  let segment = [];

  series.forEach((item, i) => {
    if (typeof item.value === 'number' && Number.isFinite(item.value)) {
      segment.push(`${x(i)},${y(item.value)}`);
    } else if (segment.length) {
      if (segment.length > 1) segments.push(segment.join(' '));
      segment = [];
    }
  });

  if (segment.length > 1) {
    segments.push(segment.join(' '));
  }

  const lines = segments.map(points =>
    `<polyline class="chart-line" points="${points}"/>`
  ).join('');

  const dots = series.map((item, i) => {
    if (typeof item.value !== 'number' || !Number.isFinite(item.value)) {
      return '';
    }

    return `
      <circle class="chart-point"
        tabindex="0"
        data-index="${i}"
        cx="${x(i)}"
        cy="${y(item.value)}"
        r="4"
        aria-label="${escapeHtml(shortPeriod(item.label))}: ${escapeHtml(metric.format(item.value))}"/>
    `;
  }).join('');

  const trendPoints = trend.map(item => {
    const i = series.findIndex(p => p.label === item.label);

    return i < 0 ? null : `${x(i)},${y(item.value)}`;
  }).filter(Boolean).join(' ');

  const trendLine = trendPoints
    ? `<polyline class="chart-trend-line" points="${trendPoints}"/>`
    : '';

  element.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="${escapeHtml(metric.label)} por periodo">

      <defs>
        <linearGradient id="${element.id}-gradient"
          x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stop-color="#54aa9f" stop-opacity=".22"/>
          <stop offset="1" stop-color="#54aa9f" stop-opacity="0"/>
        </linearGradient>
      </defs>

      ${ticks}
      ${lines}
      ${trendLine}
      ${dots}
      ${labels}
    </svg>
  `;

  const tooltip = document.createElement('div');
  tooltip.className = 'chart-tooltip';

  element.appendChild(tooltip);

  element.querySelectorAll('.chart-point').forEach(point => {
    const show = () => {
      const item = series[Number(point.dataset.index)];

      tooltip.innerHTML = `
        ${escapeHtml(formatPeriod(item.label))}
        <strong>${escapeHtml(metric.format(item.value))}</strong>
      `;

      tooltip.style.display = 'block';

      const er = element.getBoundingClientRect();
      const pr = point.getBoundingClientRect();

      tooltip.style.left = `${
        Math.max(
          4,
          Math.min(
            pr.left - er.left,
            er.width - tooltip.offsetWidth - 4
          )
        )
      }px`;

      tooltip.style.top = `${
        Math.max(
          4,
          pr.top - er.top - tooltip.offsetHeight - 9
        )
      }px`;
    };

    point.addEventListener('mouseenter', show);
    point.addEventListener('focus', show);

    point.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });

    point.addEventListener('blur', () => {
      tooltip.style.display = 'none';
    });
  });
}

function showEmpty(element, message) {
  if (!element) return;

  element.replaceChildren();

  const div = document.createElement('div');
  div.className = 'empty-state';
  div.textContent = message;

  element.appendChild(div);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

function drawRanking(element, items) {
  if (!items.length) {
    showEmpty(element, 'No hay datos disponibles para este periodo.');
    return;
  }

  const max = items[0].value || 1;

  element.innerHTML = items.map((item, index) => `
    <div class="rank-row">
      <span class="rank-number">${index + 1}</span>

      <div class="rank-content">
        <div class="rank-name">${escapeHtml(item.label)}</div>

        <div class="rank-track">
          <span style="width:${Math.max(2, item.value / max * 100)}%"></span>
        </div>
      </div>

      <span class="rank-value">
        ${numberFormat.format(item.value)} €/m²
      </span>
    </div>
  `).join('');
}

function renderSummary() {
  const rows = provincialRows();

  if (!state.summaryPeriod) {
    state.summaryPeriod = availablePeriods(rows)[0] || '';
  }

  const latest = selectedRows(rows, state.summaryPeriod)[0] || {};

  const p = typeof latest.precio_m2 === 'number'
    ? latest.precio_m2
    : null;

  const sales = typeof latest.compraventas === 'number'
    ? latest.compraventas
    : null;

  const ticket = typeof latest.importe_medio === 'number'
    ? latest.importe_medio
    : null;

  $('summary-ticket').textContent = fmtMoney(ticket);
  $('summary-sales').textContent = fmtNumber(sales);
  $('summary-price').textContent = fmtPrice(p);

  $('summary-size').textContent =
    ticket !== null && p !== null && p > 0
      ? `${new Intl.NumberFormat('es-ES', {
          maximumFractionDigits: 1
        }).format(ticket / p)} m²`
      : 'Sin datos';

  const metric = metricConfig[state.summaryMetric];

  $('summary-chart-subtitle').textContent = metric.subtitle;

  const series = monthlySeries(rows, state.summaryMetric);

  const trend = state.summaryMetric === 'compraventas'
    ? centeredAverage(series)
    : [];

  drawLine($('summary-trend'), series, metric, trend);

  const byCP = new Map();

  state.data
    .filter(row =>
      row.tipo_ambito === 'cp' &&
      row.periodo === state.summaryPeriod &&
      typeof row.precio_m2 === 'number'
    )
    .forEach(row => {
      const key = `${row.municipio}\u0000${row.cp}`;

      if (!byCP.has(key)) {
        byCP.set(key, {
          cp: String(row.cp),
          municipio: row.municipio,
          values: []
        });
      }

      byCP.get(key).values.push(row.precio_m2);
    });

  const top = [...byCP.values()]
    .map(item => ({
      label: `${item.cp} - ${item.municipio}`,
      value: item.values.reduce((a, b) => a + b, 0) / item.values.length
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5);

  drawRanking($('summary-ranking'), top);
}

function renderPostal() {
  const rows = rowsForCP();

  if (!rows.length) {
    ['cp-ticket', 'cp-sales', 'cp-price', 'cp-size'].forEach(id => {
      $(id).textContent = 'Sin datos';
    });

    showEmpty(
      $('cp-trend'),
      'No hay datos para el código postal seleccionado.'
    );

    return;
  }

  if (
    !state.cpPeriod ||
    !rows.some(row => row.periodo === state.cpPeriod)
  ) {
    state.cpPeriod = availablePeriods(rows)[0] || '';
  }

  const latest = selectedRows(rows, state.cpPeriod)[0] || {};

  const p = typeof latest.precio_m2 === 'number'
    ? latest.precio_m2
    : null;

  const sales = typeof latest.compraventas === 'number'
    ? latest.compraventas
    : null;

  const ticket = typeof latest.importe_medio === 'number'
    ? latest.importe_medio
    : null;

  $('cp-ticket').textContent = fmtMoney(ticket);
  $('cp-sales').textContent = fmtNumber(sales);
  $('cp-price').textContent = fmtPrice(p);

  $('cp-size').textContent =
    ticket !== null && p !== null && p > 0
      ? `${new Intl.NumberFormat('es-ES', {
          maximumFractionDigits: 1
        }).format(ticket / p)} m²`
      : 'Sin datos';

  const metric = metricConfig[state.cpMetric];

  $('cp-chart-subtitle').textContent = metric.subtitle;

  const series = monthlySeries(rows, state.cpMetric);

  const trend = state.cpMetric === 'compraventas'
    ? centeredAverage(series)
    : [];

  drawLine($('cp-trend'), series, metric, trend);

  if (refreshCPPeriod) refreshCPPeriod();

  renderMap();
}

function mapValues(period, key = state.mapMetric) {
  const grouped = new Map();

  state.data
    .filter(row =>
      row.tipo_ambito === 'cp' &&
      row.periodo === period &&
      typeof row[key] === 'number' &&
      Number.isFinite(row[key])
    )
    .forEach(row => {
      const cp = String(row.cp);

      if (!grouped.has(cp)) {
        grouped.set(cp, []);
      }

      grouped.get(cp).push(row[key]);
    });

  return new Map(
    [...grouped].map(([cp, values]) => [
      cp,
      values.reduce((a, b) => a + b, 0) / values.length
    ])
  );
}

function interpolateColor(value, max) {
  if (value === null || !Number.isFinite(value)) {
    return '#e7edef';
  }

  const t = Math.max(0, Math.min(1, value / (max || 1)));

  const stops = [
    { at: 0, c: [22, 127, 120] },
    { at: 0.58, c: [224, 181, 112] },
    { at: 1, c: [190, 83, 70] }
  ];

  let a = stops[0];
  let b = stops[1];

  for (let i = 1; i < stops.length; i++) {
    if (t <= stops[i].at) {
      a = stops[i - 1];
      b = stops[i];
      break;
    }

    a = stops[i - 1];
    b = stops[i];
  }

  const ratio = (t - a.at) / (b.at - a.at);

  const rgb = a.c.map((v, i) =>
    Math.round(v + (b.c[i] - v) * ratio)
  );

  return `rgb(${rgb.join(',')})`;
}

function featureCP(feature) {
  return String(feature?.properties?.COD_POSTAL ?? '').padStart(5, '0');
}

function renderMap() {
  if (!state.map || !state.geojson) return;

  const metric = metricConfig[state.mapMetric];

  const values = mapValues(state.cpPeriod, state.mapMetric);
  const max = Math.max(0, ...values.values());

  // Mostrar el periodo representado en lugar del título del gráfico.
  $('map-title').textContent = shortPeriod(state.cpPeriod);

  $('map-max-label').textContent = metric.format(max);
  $('map-min-label').textContent = metric.format(0);

  if (state.geoLayer) {
    state.map.removeLayer(state.geoLayer);
  }

  state.geoLayer = L.geoJSON(state.geojson, {
    style: feature => {
      const value = values.has(featureCP(feature))
        ? values.get(featureCP(feature))
        : null;

      return {
        color: '#ffffff',
        weight: 0.8,
        opacity: 1,
        fillColor: interpolateColor(value, max),
        fillOpacity: 0.88
      };
    },

    onEachFeature: (feature, layer) => {
      const cp = featureCP(feature);

      const value = values.has(cp)
        ? values.get(cp)
        : null;

      layer.bindTooltip(
        `<strong>CP ${escapeHtml(cp)}</strong><br>${
          value === null
            ? 'Sin datos'
            : escapeHtml(metric.format(value))
        }`,
        {
          sticky: true,
          direction: 'auto'
        }
      );

      layer.on({
        mouseover: event => {
          event.target.setStyle({
            weight: 2.2,
            color: '#153d47',
            fillOpacity: 1
          });
        },

        mouseout: event => {
          state.geoLayer.resetStyle(event.target);
        },

        click: () => {
          if (rowsForCP(cp).length) {
            state.cp = cp;
            state.cpPeriod = availablePeriods(rowsForCP())[0] || '';

            refreshCPPicker();
            renderPostal();
          }
        }
      });
    }
  }).addTo(state.map);
}

let refreshCPPicker = () => {};

async function initMap() {
  if (state.map || state.mapLoading) return;

  state.mapLoading = true;

  if (!window.L) {
    state.mapLoading = false;

    showEmpty(
      $('postal-map'),
      'No se ha podido cargar la librería cartográfica.'
    );

    return;
  }

  const geoUrl = new URL(GEO_URL, document.baseURI);
  const response = await fetch(geoUrl);

  if (!response.ok) {
    throw new Error(
      `No se pudo cargar ${geoUrl.pathname} (HTTP ${response.status}). Comprueba que malaga.geojson está dentro de data.`
    );
  }

  state.geojson = await response.json();

  if (
    !state.geojson.features ||
    !Array.isArray(state.geojson.features)
  ) {
    throw new Error(
      'El archivo malaga.geojson no contiene un GeoJSON FeatureCollection válido.'
    );
  }

  // Mapa temático sin teselas:
  // solo se dibujan los límites postales del GeoJSON de Málaga.
  state.map = L.map('postal-map', {
    scrollWheelZoom: false,
    zoomControl: false,
    attributionControl: false,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false,
    dragging: false,
    touchZoom: false
  }).setView([36.72, -4.55], 8);

  const bounds = L.geoJSON(state.geojson).getBounds();

  if (bounds.isValid()) {
    state.map.fitBounds(bounds, { padding: [8, 8] });
  }

  renderMap();
}

async function init() {
  try {
    const [dataResponse] = await Promise.all([
      fetch(DATA_URL, { cache: 'no-store' })
    ]);

    if (!dataResponse.ok) {
      throw new Error(`Error HTTP ${dataResponse.status}`);
    }

    const json = await dataResponse.json();

    if (!Array.isArray(json.datos)) {
      throw new Error('El JSON no contiene el array datos.');
    }

    state.data = json.datos;

    const cpOptions = [
      ...new Set(
        state.data
          .filter(row => row.tipo_ambito === 'cp')
          .map(row => String(row.cp))
      )
    ];

    if (!cpOptions.includes(state.cp)) {
      state.cp = cpOptions.sort()[0] || '';
    }

    state.summaryPeriod = availablePeriods(provincialRows())[0] || '';
    state.cpPeriod = availablePeriods(rowsForCP())[0] || '';

    setupPickers();

    refreshCPPicker = () => {
      $('cp-chip').textContent = state.cp;

      $('cp-menu').querySelectorAll('.period-option').forEach(button => {
        const active = button.textContent === state.cp;

        button.classList.toggle('selected', active);
        button.setAttribute('aria-selected', String(active));
      });

      if (refreshCPPeriod) {
        refreshCPPeriod();
      }
    };

    setupMetricButtons('[data-metric]', 'summaryMetric', renderSummary);
    setupMetricButtons('[data-cp-metric]', 'cpMetric', renderPostal);
    setupMetricButtons('[data-map-metric]', 'mapMetric', renderMap);

    setupNavigation();

    renderSummary();
    renderPostal();

  } catch (error) {
    console.error('Error al iniciar el dashboard:', error);

    showEmpty(
      $('summary-trend'),
      'No se han podido cargar los datos. Comprueba los archivos de la carpeta data.'
    );

    showEmpty(
      $('postal-map'),
      'No se ha podido cargar el mapa. Comprueba que data/malaga.geojson está disponible.'
    );
  }
}

document.addEventListener('DOMContentLoaded', init);

window.addEventListener('resize', () => {
  if (state.map) {
    state.map.invalidateSize();
  }
});
