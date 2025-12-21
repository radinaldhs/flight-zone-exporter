import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

from app.core.exceptions import FileProcessingError


class KMLParser:
    @staticmethod
    def parse_kmls(folder: Path) -> gpd.GeoDataFrame:
        try:
            records = []
            kml_files = list(folder.rglob('*.kml'))

            if not kml_files:
                raise FileProcessingError("No KML files found in the uploaded archive")

            for kml in kml_files:
                root = ET.parse(kml).getroot()
                for pm in root.findall('.//Placemark'):
                    name = pm.findtext('name')

                    # Build a dict of all Data tags, replacing spaces with underscores
                    props = {
                        d.attrib['name'].replace(' ', '_'): d.findtext('value')
                        for d in pm.findall('.//Data')
                    }

                    # Parse coordinates
                    coords_text = pm.findtext('.//coordinates', '')
                    coords = [
                        tuple(map(float, pt.split(',')[:2]))
                        for pt in coords_text.split()
                        if pt.strip()
                    ]

                    if not coords:
                        continue

                    rec = {'Name': name, 'geometry': LineString(coords)}
                    rec.update(props)
                    records.append(rec)

            if not records:
                raise FileProcessingError("No valid placemarks found in KML files")

            gdf = gpd.GeoDataFrame(records, crs='EPSG:4326')

            # Coerce numeric columns
            numeric_cols = [
                "Height", "Route_Spacing", "Task_Flight_Speed",
                "Task_Area", "Flight_Time", "Spray_amount"
            ]
            for numcol in numeric_cols:
                if numcol in gdf.columns:
                    gdf[numcol] = pd.to_numeric(gdf[numcol], errors='coerce')

            return gdf

        except ET.ParseError as e:
            raise FileProcessingError(f"Invalid KML format: {str(e)}")
        except Exception as e:
            raise FileProcessingError(f"KML parsing failed: {str(e)}")

    @staticmethod
    def extract_kml_metadata(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        return {
            "total_zones": len(gdf),
            "columns": gdf.columns.tolist(),
            "zone_names": gdf['Name'].tolist() if 'Name' in gdf.columns else [],
            "bounds": gdf.total_bounds.tolist() if not gdf.empty else None,
            "crs": str(gdf.crs)
        }
