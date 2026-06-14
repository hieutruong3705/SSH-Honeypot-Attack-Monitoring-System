import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

export default function AttackMap() {
  const [data, setData] = useState([])

  useEffect(() => {
    fetch('/api/map')
      .then(res => res.json())
      .then(setData)
      .catch(console.error)
      
    const interval = setInterval(() => {
      fetch('/api/map').then(r => r.json()).then(setData).catch(() => {})
    }, 10000)
    
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="card h-[400px] flex flex-col overflow-hidden relative z-0">
      <div className="px-5 py-4 border-b border-soft-border absolute top-0 left-0 right-0 bg-soft-bg/90 backdrop-blur-sm z-10">
        <h2 className="text-sm font-medium text-soft-textHover">Global Attack Map</h2>
      </div>
      <div className="flex-1 bg-soft-bg">
        <MapContainer 
          center={[20, 0]} 
          zoom={2} 
          style={{ height: '100%', width: '100%', background: '#f0f9ff' }}
          zoomControl={false}
          attributionControl={false}
          minZoom={2}
        >
          {/* CartoDB Dark Matter Base Map */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          />
          {data.map((point, idx) => {
            // Scale radius based on attack count, max 20
            const radius = Math.min(Math.max(point.cnt * 1.5, 4), 20)
            return (
              <CircleMarker
                key={idx}
                center={[point.lat, point.lon]}
                radius={radius}
                fillColor="#ef4444"
                color="#ef4444"
                weight={1}
                opacity={0.8}
                fillOpacity={0.4}
              >
                <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                  <div className="text-xs bg-soft-bg p-1 rounded">
                    <p className="font-bold text-soft-red mb-0.5">{point.ip}</p>
                    <p className="text-soft-textHover mb-0.5">{point.city}, {point.country}</p>
                    <p className="text-soft-text">Attacks: {point.cnt}</p>
                  </div>
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>
    </div>
  )
}
