const money = value => `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const number = value => Number(value || 0).toLocaleString();

async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function drawHourly(rows) {
  new Chart(document.getElementById('hourly-chart'), {
    type: 'line',
    data: { labels: rows.map(row => `${String(row.hour).padStart(2, '0')}:00`), datasets: [{ label: 'Trips', data: rows.map(row => row.trips), borderColor: '#2d75e6', backgroundColor: 'rgba(45,117,230,.12)', fill: true, tension: .35, pointRadius: 2, pointBackgroundColor: '#2d75e6' }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#edf1f2' }, ticks: { callback: value => `${(value / 1000).toFixed(0)}k` } }, x: { grid: { display: false } } } }
  });
}

function drawZones(rows) {
  new Chart(document.getElementById('zone-chart'), {
    type: 'bar',
    data: { labels: rows.slice(0, 8).map(row => row.zone_name || `Zone ${row.pickup_zone}`), datasets: [{ label: 'Trips', data: rows.slice(0, 8).map(row => row.trips), backgroundColor: '#18a878', borderRadius: 3 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, grid: { color: '#edf1f2' }, ticks: { callback: value => `${(value / 1000).toFixed(0)}k` } }, y: { grid: { display: false } } } }
  });
}

function drawRoutes(rows) {
  const body = document.getElementById('routes-body');
  body.innerHTML = rows.map((row, index) => `<tr><td>${String(index + 1).padStart(2, '0')}</td><td>${row.pickup_name || `Zone ${row.pickup_zone}`}</td><td>${row.dropoff_name || `Zone ${row.dropoff_zone}`}</td><td>${number(row.trips)}</td><td>${money(row.average_fare)}</td></tr>`).join('');
}

function drawMap(rows) {
  const container = document.getElementById('zone-map');
  if (!window.L) {
    container.innerHTML = '<div class="map-loading">Leaflet could not be loaded. Check your internet connection.</div>';
    return;
  }
  fetch('/static/data/taxi_zones.geojson').then(response => {
    if (!response.ok) throw new Error('Taxi zone GeoJSON is not available');
    return response.json();
  }).then(geojson => {
    container.innerHTML = '';
    const byZone = Object.fromEntries(rows.map(row => [String(row.pickup_zone), row]));
    const maxTrips = Math.max(...rows.map(row => row.trips), 1);
    const map = L.map(container).setView([40.73, -73.97], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    const color = trips => trips > maxTrips * .75 ? '#0d766d' : trips > maxTrips * .45 ? '#24a895' : trips > maxTrips * .2 ? '#83cfc3' : '#ccece6';
    L.geoJSON(geojson, {
      style: feature => {
        const row = byZone[String(feature.properties.LocationID)];
        return { color: '#ffffff', weight: 1, fillColor: color(row ? row.trips : 0), fillOpacity: row ? .8 : .18 };
      },
      onEachFeature: (feature, layer) => {
        const row = byZone[String(feature.properties.LocationID)];
        const zoneName = feature.properties.zone || `Zone ${feature.properties.LocationID}`;
        layer.bindPopup(`<strong>${zoneName}</strong><br>${feature.properties.borough || ''}<br>Trips: ${row ? number(row.trips) : 'No activity in top zones'}${row ? `<br>Revenue: ${money(row.revenue)}` : ''}`);
      }
    }).addTo(map);
  }).catch(error => {
    container.innerHTML = '<div class="map-loading">Map data not downloaded yet. Run: python scripts/download_zone_data.py</div>';
    console.error(error);
  });
}

function drawStreaming(rows, status) {
  document.getElementById('stream-events').textContent = number(status.events_processed);
  document.getElementById('stream-batch').textContent = status.last_batch_records ? number(status.last_batch_records) : '—';
  document.getElementById('stream-status').textContent = status.events_processed ? 'Active' : 'Waiting';
  new Chart(document.getElementById('stream-chart'), {
    type: 'bar', data: { labels: rows.map(row => `${String(row.hour).padStart(2, '0')}:00`), datasets: [{ label: 'Live trips', data: rows.map(row => row.trips), backgroundColor: '#f07844', borderRadius: 3 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#edf1f2' } }, x: { grid: { display: false } } } }
  });
}

async function loadDashboard() {
  try {
    const [health, overview, hourly, routes, zones, metadata, streaming, streamStatus] = await Promise.all([
      getJson('/api/health'), getJson('/api/overview'), getJson('/api/hourly-demand'), getJson('/api/top-routes'), getJson('/api/zone-performance'), getJson('/api/metadata'), getJson('/api/streaming-demand'), getJson('/api/streaming-status')
    ]);
    document.getElementById('status-dot').style.background = health.mongodb ? '#58d5a4' : '#f07c60';
    document.getElementById('status-text').textContent = health.mongodb ? 'MongoDB connected' : 'MongoDB unavailable';
    document.getElementById('total-trips').textContent = number(overview.total_trips);
    document.getElementById('total-revenue').textContent = money(overview.total_revenue);
    document.getElementById('average-fare').textContent = money(overview.average_fare);
    document.getElementById('average-distance').textContent = `${Number(overview.average_distance).toFixed(2)} mi`;
    document.getElementById('data-window').textContent = `${overview.data_start} — ${overview.data_end}`;
    document.getElementById('metadata').textContent = `${metadata.source} · ${metadata.engine} · ${metadata.cleaned_records ? number(metadata.cleaned_records) : '—'} records processed · ${metadata.processed_at || ''}`;
    drawHourly(hourly); drawZones(zones); drawRoutes(routes); drawMap(zones); drawStreaming(streaming, streamStatus);
  } catch (error) {
    document.getElementById('status-dot').style.background = '#f07c60';
    document.getElementById('status-text').textContent = 'Run the demo seed first';
    document.getElementById('data-window').textContent = 'No processed data available';
    document.getElementById('metadata').textContent = 'Start MongoDB and run: python scripts/seed_demo.py';
    console.error(error);
  }
}

loadDashboard();
