# Flight Zone Selector & Exporter

A Streamlit app for processing drone flight KMLs and Excel records to generate shapefiles for upload.

## Features

- **KML to Shapefile**: Parses KMLs into a merged GeoDataFrame.
- **Excel Integration**: Reads `data.xlsx`, inserts serial numbers, and builds a summary sheet.
- **QGIS Edit Workflow**: Exports shapefile ZIP for manual zone deletion.
- **Automated Pipeline**: Reimports edited shapefile or skips edit to produce final zipped shapefile and updated Excel.
- **Watermark**: Displays an unremovable watermark `© Radinal Dewantara` in the sidebar.

## Getting Started

### Prerequisites

- Python 3.8+
- [Streamlit](https://streamlit.io/)
- [GeoPandas](https://geopandas.org/)

### Installation

```bash
git clone https://github.com/yourusername/flight-zone-exporter.git
cd flight-zone-exporter
pip install -r requirements.txt
```

### Running Locally

```bash
streamlit run runner.py
```

Your app will open in the browser at `http://localhost:8501`.

## Usage

1. **Upload** your KML ZIP and Excel file in the sidebar.
2. **Enter** SPK number and KeyID.
3. **Generate** shapefile ZIP for QGIS, edit zones, and re-upload if needed.
4. **Skip** editing to run the full pipeline automatically.
5. **Download** final upload ZIP containing shapefile and updated Excel.

© Radinal Dewantara
