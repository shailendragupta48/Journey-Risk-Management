# 🗺️ Google Route Analyzer

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Folium](https://img.shields.io/badge/Folium-0.12.1-green?style=for-the-badge)](https://python-visualization.github.io/folium/)
[![Google Maps](https://img.shields.io/badge/Google_Maps_API-Powered-4285F4?style=for-the-badge&logo=google-maps&logoColor=white)](https://developers.google.com/maps)

A Python application for analyzing driving routes, detecting hazards, and identifying points of interest along the way.

## ✨ Overview

Google Route Analyzer is a powerful tool that leverages Google Maps APIs to analyze driving routes for potential hazards such as blind spots and sharp turns. The tool also identifies nearby points of interest like hospitals, police stations, gas stations, and train stations. Results are visualized on an interactive map and exported to Excel for detailed analysis.

## 🌟 Features

| Feature | Description |
|---------|-------------|
| **🚗 Route Planning** | Get directions between two points with waypoint support |
| **⚠️ Hazard Detection** | <ul><li>Sharp turns (> 35°)</li><li>Blind spots (turns > 60°)</li></ul> |
| **🏥 Points of Interest** | <ul><li>Hospitals</li><li>Police stations</li><li>Gas stations</li><li>Train stations</li></ul> |
| **🌐 Interactive Maps** | <ul><li>Color-coded icons</li><li>Turn & blind spot warnings</li><li>Live GPS tracking</li></ul> |
| **📊 Data Export** | <ul><li>Risk assessments</li><li>Turn angles</li><li>Distance measurements</li></ul> |

## 📋 Requirements

- Python 3.7+
- Google Maps Platform account with API access
- Required packages:
  ```
  folium>=0.12.1
  branca>=0.4.2
  requests>=2.25.1
  polyline>=1.4.0
  pandas>=1.3.0
  geopy>=2.2.0
  ```

## 🚀 Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/google-route-analyzer.git
cd google-route-analyzer
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Prepare your data:
   - Create an Excel file with columns: ID, Latitude, Longitude (and any other data you need)
   - Each row represents a destination with a unique ID

## 🔧 Usage

1. Update the configuration variables in the `main()` function with your own values for:
   - Excel file path
   - Output folder
   - Origin coordinates

2. Run the script:

```bash
python route_analyzer.py
```

3. The script will:
   - Process each destination in your Excel file
   - Generate an interactive HTML map for each route
   - Create an Excel file with detailed analysis for each route

## 🧭 Map Navigation

The interactive HTML maps provide a rich user experience:

- 🖱️ Click markers to see detailed information about each location
- 🔍 Use the legend to understand different map elements
- 📍 Click "Start Tracking" to enable GPS tracking of your current location

## 📱 GPS Tracking

The included GPS tracking feature allows you to:

- 📍 Track your current position on the route
- 📏 Calculate travel distance
- ⏱️ Monitor travel time
- 🎯 Get real-time location coordinates and accuracy

## 📊 Understanding the Analysis

The Excel output includes detailed analytics:

| Column | Description |
|--------|-------------|
| **Route ID** | Unique identifier for each route |
| **Category** | Type of point (Turn, Blind Spot, Hospital, etc.) |
| **Name** | Description or name of the point |
| **Coordinates** | Latitude and longitude |
| **Turn Angle** | Degrees of direction change (for turns) |
| **Risk Type** | Assessment of hazard level (Low/Medium/High) |
| **Distance to Start** | Distance from origin in kilometers |

## 🔍 Technical Details

The application leverages several advanced technologies:

### 💾 Data Processing
- Polyline encoding/decoding for efficient route representation
- Turn detection algorithms for identifying hazardous areas
- Proximity analysis for relevant point-of-interest detection

### 🎨 Visualization
- Folium for interactive map generation
- Custom icons and popups for better user experience
- GPS integration for real-time tracking

## ⚠️ Troubleshooting

Common issues and solutions:

| Problem | Solution |
|---------|----------|
| **Excel Format Issues** | Verify your Excel file has the correct column names and data types |
| **Output Folder** | Make sure the specified output folder exists or can be created |
| **Map Not Loading** | Ensure your HTML file is being opened in a modern web browser |

## 👏 Acknowledgments

- Built with Folium for interactive maps
- Leverages pandas for data processing
