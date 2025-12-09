(async () => {
  console.log('🗺️ map.js loading…');
  const { geojsons, rasters } = await fetch('/manifest.json').then(r => r.json());
  console.log('📑 manifest:', geojsons, rasters);

  // 1) Read the initial view from the map DIV’s data-attributes
  const mapDiv = document.getElementById('map');
  const initialCenter = [
    parseFloat(mapDiv.dataset.centerLng, 10),
    parseFloat(mapDiv.dataset.centerLat, 10)
  ];
  const initialZoom = parseFloat(mapDiv.dataset.zoom, 10);

  // 2) Instantiate the map
  const map = new maplibregl.Map({
    container: 'map',
    style:     'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center:    initialCenter,
    zoom:      initialZoom
  });

  map.on('load', async () => {
    map.addControl(new maplibregl.NavigationControl());
    console.log('✅ map loaded');

    // Layer controls containers
    const vectorCtrl = document.getElementById('vector-layers');
    const rasterCtrl = document.getElementById('raster-layers');
    const globalBtns = document.getElementById('global-buttons');

    // 3) ESRI World Imagery base
    map.addSource('esri-imagery', {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
      ],
      tileSize: 256
    });
    map.addLayer({
      id:     'esri-imagery',
      type:   'raster',
      source: 'esri-imagery',
      paint:  { 'raster-opacity': 1.0 }
    });
    addToggle('esri-imagery', 'ESRI World Imagery', rasterCtrl);

    // 4) NDVI rasters
    ['NDVI_2019', 'NDVI_2024'].forEach(layerId => {
      const entry = rasters.find(r => r.id === layerId);
      if (!entry) return;
      map.addSource(layerId, {
        type: 'raster',
        tiles: [`/tiles/${layerId}/{z}/{x}/{y}.png`],
        tileSize: 256
      });
      map.addLayer({
        id:     layerId,
        type:   'raster',
        source: layerId,
        paint:  { 'raster-opacity': 1.0 }
      });
      addToggle(layerId, entry.file, rasterCtrl);
    });

    // 5) GeoJSON vector layers
    const colorMap = {
      WATER: '#0077be', TREES: '#228b22', GRASS: '#00ff00',
      FOREST: '#006400', WETLAND: '#dda0dd', SHRUBS: '#a0522d',
      FLOODED_VEGETATION: '#a020f0', CROPS: '#daa520',
      BUILT: '#808080', BARE: '#d2b48c', SNOW_AND_ICE: '#fffafa',
      GREEN_INFRASTRUCTURE: '#00ff7f',
      PARKS_AND_OPEN_SPACES: 'lightgreen', TURF: 'palegreen',
      RIPARIAN: 'purple', DRAINAGE_SWALES: '#c3cd32', OK_PARKS: '#ff6347',
    };

    for (const { id, file } of geojsons) {
      map.addSource(id, { type: 'geojson', data: `/data/${file}` });
      const data = await fetch(`/data/${file}`).then(r => r.json());
      const classes = Array.from(new Set(
        data.features.map(f => f.properties.secondaryClass).filter(Boolean)
      ));
      classes.forEach(cls => {
        const layerId = `${id}_${cls.replace(/\W/g, '_')}`;
        const color   = colorMap[cls] || '#999999';
        map.addLayer({
          id:     layerId,
          type:   'fill',
          source: id,
          filter: ['==', ['get', 'secondaryClass'], cls],
          paint:  { 'fill-color': color, 'fill-opacity': 0.6 }
        });
        setupPopup(layerId);
        addToggle(layerId, cls, vectorCtrl);
      });
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
  function addToggle(layerId, label, parent) {
    const div = document.createElement('div');
    div.innerHTML = `
      <input type="checkbox" id="${layerId}" checked>
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
