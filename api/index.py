import os
import json
from flask import Flask, jsonify, Response

app = Flask(__name__)

# ───────── Paths ─────────
# In Vercel, the working directory is the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON_DIR = os.path.join(BASE_DIR, 'data', 'geojson')


def sanitize(name: str) -> str:
    """Strip extension, replace spaces and hyphens with underscores."""
    return os.path.splitext(name)[0].replace(' ', '_').replace('-', '_')


def get_geojson_map():
    """Build geojson map dynamically to handle serverless cold starts."""
    try:
        files = os.listdir(GEOJSON_DIR)
        return {
            sanitize(f): f
            for f in files
            if f.lower().endswith('.geojson')
        }
    except Exception as e:
        print(f"Error listing geojson dir: {e}")
        return {}


# Default center (Okotoks, Alberta)
DEFAULT_CENTER = (-113.9817, 50.7256)
DEFAULT_ZOOM = 13


@app.route('/')
def index():
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>NAMP Assets Demo</title>
  <link href="https://unpkg.com/maplibre-gl/dist/maplibre-gl.css" rel="stylesheet"/>
  <style>
    body, html {{ margin:0; padding:0; height:100%; }}
    #map {{ position:absolute; top:0; bottom:0; width:100%; }}
    #layer-controls {{
      position:absolute;
      top:10px; left:10px;
      background:white;
      padding:8px;
      font-family:sans-serif;
      z-index:10;
      max-height:80%; overflow-y:auto;
      border-radius: 4px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }}
    #layer-controls h3 {{ margin:4px 0; font-size:14px; }}
    #layer-controls div {{ margin-bottom:4px; }}
    button {{ margin: 2px; padding: 4px 8px; cursor: pointer; }}
  </style>
</head>
<body>
  <div id="map" data-center-lng="{DEFAULT_CENTER[0]}" data-center-lat="{DEFAULT_CENTER[1]}" data-zoom="{DEFAULT_ZOOM}"></div>

  <div id="layer-controls">
    <div id="vector-layers"><h3>Vector Layers</h3></div>
    <div id="raster-layers"><h3>Base Maps</h3></div>
    <div id="global-buttons">
      <button id="selectAll">Select All</button>
      <button id="deselectAll">Deselect All</button>
    </div>
  </div>

  <script src="https://unpkg.com/maplibre-gl/dist/maplibre-gl.js"></script>
  <script>
(async () => {{
  console.log('map.js loading...');

  let manifest;
  try {{
    manifest = await fetch('/manifest.json').then(r => r.json());
    console.log('manifest:', manifest);
  }} catch (e) {{
    console.error('Failed to fetch manifest:', e);
    return;
  }}

  const geojsons = manifest.geojsons || [];
  console.log('geojsons count:', geojsons.length);

  const mapDiv = document.getElementById('map');
  const initialCenter = [
    parseFloat(mapDiv.dataset.centerLng),
    parseFloat(mapDiv.dataset.centerLat)
  ];
  const initialZoom = parseFloat(mapDiv.dataset.zoom);

  const map = new maplibregl.Map({{
    container: 'map',
    style: {{
      version: 8,
      sources: {{
        'osm': {{
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap'
        }}
      }},
      layers: [{{ id: 'osm', type: 'raster', source: 'osm' }}]
    }},
    center: initialCenter,
    zoom: initialZoom
  }});

  map.on('load', async () => {{
    map.addControl(new maplibregl.NavigationControl());
    console.log('map loaded');

    const vectorCtrl = document.getElementById('vector-layers');
    const rasterCtrl = document.getElementById('raster-layers');
    const globalBtns = document.getElementById('global-buttons');

    // ESRI Satellite
    map.addSource('esri-imagery', {{
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}'],
      tileSize: 256
    }});
    map.addLayer({{
      id: 'esri-imagery',
      type: 'raster',
      source: 'esri-imagery',
      layout: {{ visibility: 'none' }},
      paint: {{ 'raster-opacity': 1.0 }}
    }});
    addToggle('esri-imagery', 'ESRI Satellite', rasterCtrl, false);

    const colorMap = {{
      WATER: '#0077be', TREES: '#228b22', GRASS: '#00ff00',
      FOREST: '#006400', WETLAND: '#dda0dd', SHRUBS: '#a0522d',
      FLOODED_VEGETATION: '#a020f0', CROPS: '#daa520',
      BUILT: '#808080', BARE: '#d2b48c', SNOW_AND_ICE: '#fffafa',
      GREEN_INFRASTRUCTURE: '#00ff7f',
      PARKS_AND_OPEN_SPACES: 'lightgreen', TURF: 'palegreen',
      RIPARIAN: 'purple', DRAINAGE_SWALES: '#c3cd32', OK_PARKS: '#ff6347',
      AGR: '#daa520', BLT: '#808080', BRE: '#d2b48c', FRT: '#006400',
      GRS: '#00ff00', SHR: '#a0522d', WTD: '#dda0dd', WTR: '#0077be',
    }};

    const defaultColors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf'];
    let colorIndex = 0;

    for (const {{ id, file }} of geojsons) {{
      console.log('Loading GeoJSON:', id, file);
      try {{
        const data = await fetch('/data/' + file).then(r => r.json());
        map.addSource(id, {{ type: 'geojson', data: data }});

        const classes = Array.from(new Set(
          data.features.map(f => f.properties.secondaryClass).filter(Boolean)
        ));

        if (classes.length > 0) {{
          classes.forEach(cls => {{
            const layerId = id + '_' + cls.replace(/\\W/g, '_');
            const color = colorMap[cls] || defaultColors[colorIndex++ % defaultColors.length];
            map.addLayer({{
              id: layerId,
              type: 'fill',
              source: id,
              filter: ['==', ['get', 'secondaryClass'], cls],
              paint: {{ 'fill-color': color, 'fill-opacity': 0.6 }}
            }});
            setupPopup(layerId);
            addToggle(layerId, id + ' - ' + cls, vectorCtrl);
          }});
        }} else {{
          const color = defaultColors[colorIndex++ % defaultColors.length];
          map.addLayer({{
            id: id,
            type: 'fill',
            source: id,
            paint: {{ 'fill-color': color, 'fill-opacity': 0.6 }}
          }});
          setupPopup(id);
          addToggle(id, id, vectorCtrl);
        }}
        console.log('Loaded:', id);
      }} catch (e) {{
        console.error('Failed to load ' + file + ':', e);
      }}
    }}

    globalBtns.querySelector('#selectAll').onclick = () => {{
      [...vectorCtrl.querySelectorAll('input'), ...rasterCtrl.querySelectorAll('input')]
        .forEach(cb => {{
          cb.checked = true;
          map.setLayoutProperty(cb.id, 'visibility', 'visible');
        }});
    }};
    globalBtns.querySelector('#deselectAll').onclick = () => {{
      [...vectorCtrl.querySelectorAll('input'), ...rasterCtrl.querySelectorAll('input')]
        .forEach(cb => {{
          cb.checked = false;
          map.setLayoutProperty(cb.id, 'visibility', 'none');
        }});
    }};
  }});

  function addToggle(layerId, label, parent, checked = true) {{
    const div = document.createElement('div');
    div.innerHTML = '<input type="checkbox" id="' + layerId + '" ' + (checked ? 'checked' : '') + '><label for="' + layerId + '">' + label + '</label>';
    div.querySelector('input').addEventListener('change', e => {{
      map.setLayoutProperty(layerId, 'visibility', e.target.checked ? 'visible' : 'none');
    }});
    parent.appendChild(div);
  }}

  function setupPopup(layerId) {{
    map.on('click', layerId, e => {{
      const props = e.features[0].properties;
      const html = Object.entries(props).map(([k, v]) => '<b>' + k + ':</b> ' + v).join('<br>');
      new maplibregl.Popup().setLngLat(e.lngLat).setHTML(html).addTo(map);
    }});
  }}
}})();
  </script>
</body>
</html>'''
    return Response(html, mimetype='text/html')


@app.route('/manifest.json')
def manifest():
    geojson_map = get_geojson_map()
    geojsons = [{'id': _id, 'file': fname} for _id, fname in geojson_map.items()]
    return jsonify({'geojsons': geojsons})


@app.route('/data/<path:filename>')
def data(filename):
    filepath = os.path.join(GEOJSON_DIR, filename)
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return Response(content, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), status=404, mimetype='application/json')


# Vercel handler
app = app
