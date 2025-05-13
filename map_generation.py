
import folium
import branca
import requests
import polyline
import time
import os
import math
import pandas as pd
from geopy.distance import geodesic
from typing import List, Dict, Tuple

class GoogleRouteAnalyzer:
    def __init__(self, api_key, excel_path, output_folder):
        self.api_key = api_key
        self.excel_path = excel_path
        self.output_folder = output_folder
        self.directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        # Updated Places API endpoint
        self.places_url = "https://places.googleapis.com/v1/places:searchNearby"
        self.snap_to_roads_url = "https://roads.googleapis.com/v1/snapToRoads"
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
    
    def read_route_data(self, route_id):
        """Read route data from Excel file based on ID."""
        try:
            # Read the Excel file
            df = pd.read_excel(self.excel_path)
            
            # Filter data for the given ID
            route_data = df[df['ID'] == route_id].iloc[0]
            
            # Extract coordinates and waypoints
            destination = (float(route_data['Latitude']), float(route_data['Longitude']))
            
            return destination
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return None

    def calculate_bearing(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        lat1, lon1 = map(math.radians, point1)
        lat2, lon2 = map(math.radians, point2)

        d_lon = lon2 - lon1
        x = math.sin(d_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        
        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        return (bearing + 360) % 360

    def calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        R = 6371000  # Earth's radius in meters
        lat1, lon1 = map(math.radians, point1)
        lat2, lon2 = map(math.radians, point2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def detect_turns(self, points: List[Tuple[float, float]], 
                    min_angle: float = 45.0,
                    min_distance: float = 50.0,
                    blind_spot_threshold: float = 60.0,
                    sliding_window: int = 3) -> List[Dict]:
        turns = []

        if len(points) < sliding_window + 1:
            return turns

        for i in range(1, len(points) - sliding_window):
            prev_point = points[i - 1]
            next_point = points[i + sliding_window - 1]

            bearing_start = self.calculate_bearing(prev_point, points[i])
            bearing_end = self.calculate_bearing(points[i], next_point)
            bearing_change = abs((bearing_end - bearing_start + 180) % 360 - 180)

            if bearing_change >= min_angle:
                if not turns or self.calculate_distance(turns[-1]['point'], points[i]) >= min_distance:
                    turn = {
                        'point': points[i],
                        'angle': round(bearing_change, 1),
                        'is_blind_spot': bearing_change >= blind_spot_threshold
                    }
                    turns.append(turn)

        return turns

    def get_route(self, origin, destination):
        """
        Get route with support for coordinate-based origin/destination and waypoints
        """
        try:
            params = {
                'origin': f"{origin[0]},{origin[1]}",
                'destination': f"{destination[0]},{destination[1]}",
                'mode': 'driving',
                'key': self.api_key
            }

            response = requests.get(self.directions_url, params=params)
            response.raise_for_status()
            route_data = response.json()
            
            if route_data['status'] != 'OK':
                raise Exception(f"Directions API error: {route_data['status']}")
                    
            return route_data
        except Exception as e:
            print(f"Error fetching route: {e}")
            return None

    def snap_to_roads(self, route_points):
        snapped_points = []

        # Split points into chunks of 100
        chunk_size = 100
        for i in range(0, len(route_points), chunk_size):
            chunk = route_points[i:i + chunk_size]
            path = '|'.join([f"{point[0]},{point[1]}" for point in chunk])
            
            params = {
                'path': path,
                'interpolate': True,
                'key': self.api_key
            }

            try:
                response = requests.get(self.snap_to_roads_url, params=params)
                response.raise_for_status()
                snapped_data = response.json()

                snapped_points.extend([
                    (point['location']['latitude'], point['location']['longitude'])
                    for point in snapped_data['snappedPoints']
                ])
            except Exception as e:
                print(f"Error snapping points in chunk {i // chunk_size + 1}: {e}")
        
        print(f"Snapped {len(snapped_points)} points to roads.")
        return snapped_points


    def get_places_along_route(self, snapped_points, place_types, radius=1000, proximity_threshold=100):
        places = []
        sampled_points = snapped_points[::10]
        print(f"Processing {len(sampled_points)} points along the snapped route...")

        # Map old place types to new ones
        place_type_mapping = {
            'hospital': 'hospital',
            'police': 'police_station',
            'gas_station': 'gas_station',
            'train_station': 'train_station'
        }

        for idx, point in enumerate(sampled_points):
            for place_type in place_types:
                try:
                    # Map the old place type to new format
                    new_place_type = place_type_mapping.get(place_type, place_type)
                    
                    # Create request body for new Places API
                    request_body = {
                        "locationRestriction": {
                            "circle": {
                                "center": {
                                    "latitude": point[0],
                                    "longitude": point[1]
                                },
                                "radius": radius
                            }
                        },
                        "includedTypes": [new_place_type],
                        "maxResultCount": 20
                    }
                    
                    # Set up headers with API key
                    headers = {
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": self.api_key,
                        "X-Goog-FieldMask": "places.displayName,places.location,places.formattedAddress"
                    }
                    
                    # Make the request
                    response = requests.post(self.places_url, json=request_body, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Process results
                    if 'places' in data:
                        for result in data['places']:
                            place_location = (
                                result['location']['latitude'],
                                result['location']['longitude']
                            )
                            closest_distance = min(
                                geodesic(place_location, snapped_point).meters
                                for snapped_point in snapped_points
                            )
                            if closest_distance <= proximity_threshold:
                                place = {
                                    'name': result.get('displayName', {}).get('text', 'Unnamed Place'),
                                    'location': place_location,
                                    'type': place_type,
                                    'address': result.get('formattedAddress', 'No address available')
                                }
                                places.append(place)
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        print("Rate limit reached. Pausing for 2 seconds...")
                        time.sleep(2)
                except Exception as e:
                    print(f"Error fetching POIs at point {idx}: {e}")
                    continue
        
        return places

    def create_map(self, origin, destination, route_id):
        route_data = self.get_route(origin, destination)
        if not route_data:
            print("No route data available.")
            return None

        route = route_data['routes'][0]
        leg = route['legs'][0]
        original_points = polyline.decode(route['overview_polyline']['points'])

        print(f"Route fetched with {len(original_points)} points.")
        snapped_points = self.snap_to_roads(original_points)

        # Detect turns and blind spots
        turns = self.detect_turns(
            snapped_points,
            min_angle=35.0,
            min_distance=50.0,
            blind_spot_threshold=60.0,
            sliding_window=3
        )

        # Count blind spots
        blind_spots = [turn for turn in turns if turn['is_blind_spot']]

        # Detect POIs
        place_types = ['hospital', 'police', 'gas_station', 'train_station']
        pois = self.get_places_along_route(snapped_points, place_types)

        # Collect data for Excel export
        marker_data = []

        # Create the map
        m = folium.Map(location=origin, zoom_start=12)

        # Add route polyline
        folium.PolyLine(snapped_points, weight=5, color="blue", opacity=0.8).add_to(m)

        # Define custom icons for places
        place_icons = {
            'hospital': {'icon': 'plus', 'color': 'red', 'prefix': 'fa'},
            'police': {'icon': 'shield', 'color': 'blue', 'prefix': 'fa'},
            'gas_station': {'icon': 'gas-pump', 'color': 'orange', 'prefix': 'fa'},
            'train_station': {'icon': 'train', 'color': 'purple', 'prefix': 'fa'}
        }

        # Add turn and blind spot markers
        for turn in turns:
            category = 'Blind Spot' if turn['is_blind_spot'] else 'Turn'
            marker_data.append({
                'Category': category,
                'Latitude': turn['point'][0],
                'Longitude': turn['point'][1],
                'Name': f"Turn Angle: {turn['angle']}°"
            })

            if turn['is_blind_spot']:
                # Create circle marker for blind spot area
                folium.CircleMarker(
                    location=turn['point'],
                    radius=10,
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.3
                ).add_to(m)
                
                # Add warning icon
                folium.Marker(
                    location=turn['point'],
                    popup=f"""
                        <div style="font-family: Arial, sans-serif;">
                            <h4 style="color: red;">⚠️ BLIND SPOT WARNING ⚠️</h4>
                            <b>Turn Angle:</b> {turn['angle']}°<br>
                            <b>Hazard Level:</b> High<br>
                            <small>Exercise extreme caution!</small>
                        </div>
                    """,
                    icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa')
                ).add_to(m)
            else:
                folium.Marker(
                    location=turn['point'],
                    popup=f"Turn Angle: {turn['angle']}°",
                    icon=folium.Icon(color='yellow', icon='refresh', prefix='fa')
                ).add_to(m)

        # Add POI markers with custom icons
        for poi in pois:
            marker_data.append({
                'Category': poi['type'].capitalize(),
                'Latitude': poi['location'][0],
                'Longitude': poi['location'][1],
                'Name': poi['name']
            })

            icon_config = place_icons.get(poi['type'], {'icon': 'info-sign', 'color': 'gray', 'prefix': 'fa'})
            popup_text = f"""
                <div style="font-family: Arial, sans-serif;">
                    <h4>{poi['name']}</h4>
                    <b>Type:</b> {poi['type'].capitalize()}<br>
                    <b>Address:</b> {poi['address']}<br>
                    <small>Lat: {poi['location'][0]}, Lon: {poi['location'][1]}</small>
                </div>
            """
            folium.Marker(
                location=poi['location'],
                popup=popup_text,
                icon=folium.Icon(**icon_config)
            ).add_to(m)

        # Add start marker with detailed information
        start_popup = f"""
            <div style="font-family: Arial, sans-serif;">
                <h4>Route Information</h4>
                <b>Start:</b> {leg['start_address']}<br>
                <b>Distance:</b> {leg['distance']['text']}<br>
                <b>Duration:</b> {leg['duration']['text']}<br>
                <b>Total Turns:</b> {len(turns)}<br>
                <b>Blind Spots:</b> {len(blind_spots)}<br>
                <small>Exercise caution at marked hazard points</small>
            </div>
        """
        folium.Marker(
            origin,
            popup=start_popup,
            icon=folium.Icon(color="green", icon="flag", prefix="fa")
        ).add_to(m)

        # Add end marker
        folium.Marker(
            destination,
            popup=f"End: {leg['end_address']}",
            icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa")
        ).add_to(m)

        # Add HTML legend
        legend_html = '''
            <div style="position: fixed; 
                        top: 10px; right: 10px; width: 150px;
                        border:2px solid grey; z-index:9999; font-size:14px;
                        background-color: white;
                        padding: 10px;
                        border-radius: 5px;">
                <h4 style="margin-bottom: 10px;">Legend</h4>
                <div style="margin-bottom: 5px;"><i class="fa fa-plus fa-lg" style="color:red"></i> Hospital</div>
                <div style="margin-bottom: 5px;"><i class="fa fa-shield fa-lg" style="color:blue"></i> Police</div>
                <div style="margin-bottom: 5px;"><i class="fa fa-gas-pump fa-lg" style="color:orange"></i> Gas Station</div>
                <div style="margin-bottom: 5px;"><i class="fa fa-train fa-lg" style="color:purple"></i> Train Station</div>
                <div style="margin-bottom: 5px;"><i class="fa fa-refresh fa-lg" style="color:yellow"></i> Turn</div>
                <div style="margin-bottom: 5px;"><i class="fa fa-exclamation-triangle fa-lg" style="color:red"></i> Blind Spot</div>
                <div style="margin-bottom: 5px;"><i class="fa fa-flag fa-lg" style="color:green"></i> Start</div>
                <div><i class="fa fa-flag-checkered fa-lg" style="color:red"></i> End</div>
            </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Save the marker data to Excel
        self.save_to_excel(marker_data, origin, route_id)

        return m, marker_data

    def save_to_excel(self, marker_data, origin, route_id):
        """Save route analysis data to Excel file."""
        try:
            # Modify the marker_data to include turn angle, risk type, and distance to start
            enhanced_marker_data = []
            for marker in marker_data:
                # Extract turn angle from the Name field for turns and blind spots
                turn_angle = 0
                risk_type = "Low Risk"
                
                if marker['Category'] in ['Turn', 'Blind Spot']:
                    # Extract turn angle from the Name field
                    angle_match = marker['Name'].split(': ')
                    if len(angle_match) > 1:
                        try:
                            turn_angle = float(angle_match[1].rstrip('°'))
                            
                            # Determine risk type based on turn angle
                            if turn_angle >= 60:
                                risk_type = "High Risk"
                            elif turn_angle >= 35:
                                risk_type = "Medium Risk"
                            else:
                                risk_type = "Low Risk"
                        except ValueError:
                            pass
                
                # Calculate distance to start
                marker_location = (marker['Latitude'], marker['Longitude'])
                distance_to_start = self.calculate_distance(origin, marker_location)
                
                enhanced_marker = marker.copy()
                enhanced_marker['Route ID'] = route_id  # Add route_id to each row
                enhanced_marker['Turn Angle'] = turn_angle
                enhanced_marker['Risk Type'] = risk_type
                enhanced_marker['Distance to Start (km)'] = round(distance_to_start/1000, 2)
                
                enhanced_marker_data.append(enhanced_marker)
            
            # Create DataFrame with enhanced data
            df = pd.DataFrame(enhanced_marker_data)
            
            # Reorder columns to place new columns in a logical order
            columns_order = [
                'Route ID',
                'Category',
                'Name',
                'Latitude',
                'Longitude',
                'Turn Angle',
                'Risk Type',
                'Distance to Start (km)'
            ]
            df = df[columns_order]
            
            # Create the output filename with route_id
            file_path = os.path.join(self.output_folder, f'{route_id}.xlsx')
            
            # Save to Excel with formatting
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Route Analysis')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Route Analysis']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length

            print(f"Excel file generated successfully at: {file_path}")
            
        except Exception as e:
            print(f"Error saving data to Excel: {e}")
            raise  # Re-raise the exception for better error tracking

def save_map(map_obj, output_folder, route_id):
    try:
        # The GPS tracking script remains largely the same as before
        gps_script = """
        <div id="gps-tracking" style="
            position: fixed; 
            top: 10px; 
            right: 10px; 
            background: white; 
            padding: 10px; 
            border: 1px solid #ccc; 
            z-index: 1000; 
            font-family: Arial, sans-serif;
        ">
            <button id="start-tracking" style="
                background-color: green; 
                color: white; 
                border: none; 
                padding: 10px; 
                margin-bottom: 10px;
                cursor: pointer;
            ">Start Tracking</button>
            <div id="gps-status">GPS: Not Connected</div>
            <div id="gps-coordinates"></div>
            <div id="tracking-info"></div>
        </div>
        <script>
        function initGPS() {
            const startButton = document.getElementById('start-tracking');
            const gpsStatus = document.getElementById('gps-status');
            const gpsCoordinates = document.getElementById('gps-coordinates');
            const trackingInfo = document.getElementById('tracking-info');
            let userMarker = null;
            let trackingStarted = false;
            let trackingStartTime = null;
            let totalDistance = 0;
            let previousPosition = null;

            function updateGPSMarker(lat, lon) {
                if (!userMarker) {
                    userMarker = L.marker([lat, lon], {
                        icon: L.divIcon({
                            className: 'custom-gps-marker',
                            html: `<div style="
                                width: 30px; 
                                height: 30px; 
                                background-color: green; 
                                border-radius: 50%; 
                                border: 3px solid white;
                                box-shadow: 0 0 15px rgba(0,255,0,0.5);
                            "></div>`,
                            iconSize: [30, 30],
                            iconAnchor: [15, 15]
                        })
                    }).addTo(map);
                } else {
                    // Calculate distance moved
                    if (previousPosition && trackingStarted) {
                        const distanceMoved = L.latLng([lat, lon]).distanceTo(previousPosition);
                        totalDistance += distanceMoved;
                    }
                    
                    userMarker.setLatLng([lat, lon]);
                    previousPosition = L.latLng([lat, lon]);
                }
                
                // Center map on current location
                map.setView([lat, lon], map.getZoom());
            }

            startButton.addEventListener('click', function() {
                if (!trackingStarted) {
                    trackingStarted = true;
                    trackingStartTime = new Date();
                    startButton.textContent = 'Stop Tracking';
                    startButton.style.backgroundColor = 'red';
                    trackingInfo.innerHTML = 'Tracking started...';
                } else {
                    trackingStarted = false;
                    const trackingDuration = (new Date() - trackingStartTime) / 1000 / 60; // minutes
                    trackingInfo.innerHTML = `
                        Tracking stopped<br>
                        Duration: ${trackingDuration.toFixed(2)} minutes<br>
                        Total Distance: ${(totalDistance / 1000).toFixed(2)} km
                    `;
                    startButton.textContent = 'Start Tracking';
                    startButton.style.backgroundColor = 'green';
                }
            });

            if ('geolocation' in navigator) {
                navigator.geolocation.watchPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        const accuracy = position.coords.accuracy;

                        updateGPSMarker(lat, lon);
                        
                        gpsStatus.innerHTML = 'GPS: Connected';
                        gpsCoordinates.innerHTML = `
                            Latitude: ${lat.toFixed(6)}<br>
                            Longitude: ${lon.toFixed(6)}<br>
                            Accuracy: ${accuracy.toFixed(2)} meters
                        `;

                        if (trackingStarted) {
                            trackingInfo.innerHTML = `
                                Tracking Active<br>
                                Total Distance: ${(totalDistance / 1000).toFixed(2)} km
                            `;
                        }
                    },
                    function(error) {
                        gpsStatus.innerHTML = `GPS Error: ${error.message}`;
                        console.error('Geolocation error:', error);
                    },
                    {
                        enableHighAccuracy: true,
                        maximumAge: 30000,
                        timeout: 27000
                    }
                );
            } else {
                gpsStatus.innerHTML = 'Geolocation not supported';
            }
        }

        // Initialize GPS tracking after map load
        map.whenReady(initGPS);
        </script>
        """
        
        # Add the GPS tracking HTML and script to the map
        map_obj.get_root().html.add_child(folium.Element(gps_script))
        # Add GPS tracking HTML and script
        gps_tracking_html = '''
        <div id="gps-tracking" style="
            position: fixed; 
            top: 10px; 
            right: 10px; 
            background: white; 
            padding: 10px; 
            border: 1px solid #ccc; 
            z-index: 1000; 
            font-family: Arial, sans-serif;
        ">
            <button id="start-tracking">Start Tracking</button>
            <div id="gps-status">GPS: Disconnected</div>
        </div>
        <script>
        var userMarker = null;
        document.getElementById('start-tracking').addEventListener('click', function() {
            if ('geolocation' in navigator) {
                navigator.geolocation.watchPosition(function(position) {
                    var lat = position.coords.latitude;
                    var lon = position.coords.longitude;
                    
                    document.getElementById('gps-status').innerHTML = 
                        `GPS: Active (${lat.toFixed(6)}, ${lon.toFixed(6)})`;
                    
                    if (!userMarker) {
                        userMarker = L.marker([lat, lon]).addTo(map);
                    } else {
                        userMarker.setLatLng([lat, lon]);
                    }
                    
                    map.setView([lat, lon], map.getZoom());
                });
            }
        });
        </script>
        '''
        map_obj.get_root().html.add_child(folium.Element(gps_tracking_html))
        
        file_path = os.path.join(output_folder, f'{route_id}.html')
        map_obj.save(file_path)
        print(f"Map saved to: {file_path}")
    except Exception as e:
        print(f"Error saving map: {e}")

def main():
    try:
        # Configuration
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
        raise ValueError("API key not found. Please set the GOOGLE_MAPS_API_KEY environment variable.")
        excel_path =  #Path of excel file
        output_folder = #Path of output folder
        origin = ()  # Fixed origin point
        
        # Initialize analyzer
        analyzer = GoogleRouteAnalyzer(api_key, excel_path, output_folder)
        
        # Read the Excel file to get all route IDs
        df = pd.read_excel(excel_path)
        route_ids = df['ID'].unique()
        
        # Process each route
        for route_id in route_ids:
            print(f"\nProcessing route {route_id}")
            
            # Get destination and waypoints for this route
            destination = analyzer.read_route_data(route_id)
            
            if destination:
                # Create map for this route
                route_map, marker_data = analyzer.create_map(origin, destination, route_id)
                if route_map:
                    # Save map
                    save_map(route_map, output_folder, route_id)
                    print(f"Route {route_id} processed successfully")
                else:
                    print(f"Failed to create map for route {route_id}")
            else:
                print(f"Failed to read data for route {route_id}")
                
    except Exception as e:
        print(f"Error in main: {e}")
        raise  # Re-raise the exception for better error tracking

if __name__ == "__main__":
    main()
