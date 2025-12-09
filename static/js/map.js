(async () => {
  console.log('🗺️ map.js loading…');

  let manifest;
  try {
    manifest = await fetch('/manifest.json').then(r => r.json());
    console.log('📑 manifest:', manifest);
  } catch (e) {
    console.error('❌ Failed to fetch manifest:', e);
    return;
  }

  const geojsons = manifest.geojsons || [];
  console.log('📑 geojsons count:', geojsons.length);

  // 1) Read the initial view from the map DIV's data-attributes
  const mapDiv = document.getElementById('map');
  const initialCenter = [
    parseFloat(mapDiv.dataset.centerLng, 10),
    parseFloat(mapDiv.dataset.centerLat, 10)
  ];
  const initialZoom = parseFloat(mapDiv.dataset.zoom, 10);

  // 2) Instantiate the map with inline style (no external style.json dependency)
  const map = new maplibregl.Map({
    container: 'map',
    style: {
      version: 8,
      sources: {
        'osm': {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap'
        }
      },
      layers: [{
        id: 'osm',
        type: 'raster',
        source: 'osm'
      }]
    },
    center: initialCenter,
    zoom: initialZoom
  });

  map.on('load', async () => {
    map.addControl(new maplibregl.NavigationControl());
    console.log('✅ map loaded');

    // Layer controls containers
    const vectorCtrl = document.getElementById('vector-layers');
    const rasterCtrl = document.getElementById('raster-layers');
    const globalBtns = document.getElementById('global-buttons');

    // 3) ESRI World Imagery as optional layer
    map.addSource('esri-imagery', {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
      ],
      tileSize: 256
    });
    map.addLayer({
      id: 'esri-imagery',
      type: 'raster',
      source: 'esri-imagery',
      layout: { visibility: 'none' },
      paint: { 'raster-opacity': 1.0 }
    });
    addToggle('esri-imagery', 'ESRI Satellite', rasterCtrl, false);

    // 5) GeoJSON vector layers
    const colorMap = {
      WATER: '#0077be', TREES: '#228b22', GRASS: '#00ff00',
      FOREST: '#006400', WETLAND: '#dda0dd', SHRUBS: '#a0522d',
      FLOODED_VEGETATION: '#a020f0', CROPS: '#daa520',
      BUILT: '#808080', BARE: '#d2b48c', SNOW_AND_ICE: '#fffafa',
      GREEN_INFRASTRUCTURE: '#00ff7f',
      PARKS_AND_OPEN_SPACES: 'lightgreen', TURF: 'palegreen',
      RIPARIAN: 'purple', DRAINAGE_SWALES: '#c3cd32', OK_PARKS: '#ff6347',
      AGR: '#daa520', BLT: '#808080', BRE: '#d2b48c', FRT: '#006400',
      GRS: '#00ff00', SHR: '#a0522d', WTD: '#dda0dd', WTR: '#0077be',
    };

    const defaultColors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf'];
    let colorIndex = 0;

    for (const { id, file } of geojsons) {
      console.log(`📦 Loading GeoJSON: ${id} (${file})`);
      try {
        const data = await fetch(`/data/${file}`).then(r => r.json());
        map.addSource(id, { type: 'geojson', data: data });

        const classes = Array.from(new Set(
          data.features.map(f => f.properties.secondaryClass).filter(Boolean)
        ));

        if (classes.length > 0) {
          // Has secondaryClass - create sublayers
          classes.forEach(cls => {
            const layerId = `${id}_${cls.replace(/\W/g, '_')}`;
            const color = colorMap[cls] || defaultColors[colorIndex++ % defaultColors.length];
            map.addLayer({
              id: layerId,
              type: 'fill',
              source: id,
              filter: ['==', ['get', 'secondaryClass'], cls],
              paint: { 'fill-color': color, 'fill-opacity': 0.6 }
            });
            setupPopup(layerId);
            addToggle(layerId, `${id} - ${cls}`, vectorCtrl);
          });
        } else {
          // No secondaryClass - add as single layer
          const color = defaultColors[colorIndex++ % defaultColors.length];
          map.addLayer({
            id: id,
            type: 'fill',
            source: id,
            paint: { 'fill-color': color, 'fill-opacity': 0.6 }
          });
          setupPopup(id);
          addToggle(id, id, vectorCtrl);
        }
        console.log(`✅ Loaded: ${id}`);
      } catch (e) {
        console.error(`❌ Failed to load ${file}:`, e);
      }
    }

    // 6) Global Select / Deselect All
    globalBtns.querySelector('#selectAll').onclick = () => {
      [...vectorCtrl.querySelectorAll('input'),
       ...rasterCtrl.querySelectorAll('input')]
        .forEach(cb => {
          cb.checked = true;
          map.setLayoutProperty(cb.id, 'visibility', 'visible');
        });
    };
    globalBtns.querySelector('#deselectAll').onclick = () => {
      [...vectorCtrl.querySelectorAll('input'),
       ...rasterCtrl.querySelectorAll('input')]
        .forEach(cb => {
          cb.checked = false;
          map.setLayoutProperty(cb.id, 'visibility', 'none');
        });
    };

    // Debug: list all layers
    setTimeout(() => {
      console.log('🎨 ALL LAYER IDs:', map.getStyle().layers.map(l => l.id));
    }, 1000);
  });

  // Helpers
  function addToggle(layerId, label, parent, checked = true) {
    const div = document.createElement('div');
    div.innerHTML = `
      <input type="checkbox" id="${layerId}" ${checked ? 'checked' : ''}>
      <label for="${layerId}">${label}</label>
    `;
    div.querySelector('input').addEventListener('change', e => {
      map.setLayoutProperty(layerId, 'visibility',
        e.target.checked ? 'visible' : 'none'
      );
    });
    parent.appendChild(div);
  }

  function setupPopup(layerId) {
    map.on('click', layerId, e => {
      const props = e.features[0].properties;
      const html  = Object.entries(props)
        .map(([k, v]) => `<b>${k}:</b> ${v}`)
        .join('<br>');
      new maplibregl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(html)
        .addTo(map);
    });
  }
})();
