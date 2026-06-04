import zipfile
import shutil
from pathlib import Path
from typing import Optional
import pandas as pd
import geopandas as gpd

from app.core.config import settings
from app.core.exceptions import FileProcessingError


def _normalize_header(value) -> str:
    """Trim, collapse internal whitespace, and casefold a header for tolerant matching."""
    return " ".join(str(value).split()).casefold() if value is not None else ""


class ShapefileService:
    @staticmethod
    def _resolve_column(normalized_map: dict, label: str, *, exact: str = None, prefix: str = None) -> str:
        """Return the real df column whose normalized header matches `exact` or starts with `prefix`.

        Raises FileProcessingError listing the actual columns if none match.
        """
        if exact is not None:
            match = normalized_map.get(exact)
            if match is not None:
                return match
        if prefix is not None:
            candidates = [k for k in normalized_map if k.startswith(prefix)]
            if candidates:
                return normalized_map[min(candidates, key=len)]

        raise FileProcessingError(
            f"Flight record is missing the required '{label}' column. "
            f"Found columns: {list(normalized_map.values())}"
        )

    @staticmethod
    def create_shapefile_for_edit(gdf: gpd.GeoDataFrame, spk_number: str, work_dir: Path) -> Path:
        try:
            shp_path = work_dir / f"{spk_number}_zones.shp"
            gdf.to_file(shp_path, driver='ESRI Shapefile')

            # Create ZIP with shapefile components
            edit_zip = work_dir / "zones_for_edit.zip"
            with zipfile.ZipFile(edit_zip, 'w', zipfile.ZIP_DEFLATED) as z:
                for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
                    p = shp_path.with_suffix(f'.{ext}')
                    if p.exists():
                        z.write(p, p.name)

            return edit_zip

        except Exception as e:
            raise FileProcessingError(f"Shapefile creation failed: {str(e)}")

    @staticmethod
    def process_excel(excel_path: Path, merged_gdf: gpd.GeoDataFrame, spk_number: str, key_id: str) -> tuple:
        try:
            df_flight = pd.read_excel(excel_path, sheet_name='flight record', engine='openpyxl')
            normalized_map = {_normalize_header(c): c for c in df_flight.columns}

            serial_col = ShapefileService._resolve_column(normalized_map, 'Serial Number', exact='serial number')
            flight_time_col = ShapefileService._resolve_column(normalized_map, 'Flight time', exact='flight time')
            total_amount_col = ShapefileService._resolve_column(
                normalized_map, 'Total Amount(L/Kg)', prefix='total amount'
            )

            merged_filtered = merged_gdf[
                merged_gdf['Name'].astype(str).isin(df_flight[serial_col].astype(str))
            ].reset_index(drop=True)

            if merged_filtered.empty:
                raise FileProcessingError(
                    f"No flight zones matched the '{serial_col}' values in the flight record. "
                    f"Check that the Excel serial numbers correspond to the KML placemark names "
                    f"(e.g. the KML uses names like 'R2543821792')."
                )

            df_summary = pd.DataFrame({'Name': merged_filtered['Name']})

            def lookup(serial, column):
                sub = df_flight[df_flight[serial_col].astype(str) == str(serial)]
                return sub.iloc[0][column] if not sub.empty else None

            df_summary['TaskAmount'] = df_summary['Name'].map(lambda s: (lookup(s, total_amount_col) or 0) * 1000)
            df_summary['StarFlight'] = df_summary['Name'].map(lambda s: str(lookup(s, flight_time_col) or '')[:19])
            df_summary['EndFlight'] = df_summary['Name'].map(
                lambda s: (lambda v: str(v)[:11] + str(v)[-8:])(lookup(s, flight_time_col))
            )
            df_summary['Capacity'] = 25
            df_summary['SPKNumber'] = spk_number
            df_summary['KeyID'] = key_id

            with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as w:
                df_summary.to_excel(w, sheet_name='Sheet1', index=False)

            return merged_filtered, df_summary

        except FileProcessingError:
            raise
        except Exception as e:
            raise FileProcessingError(f"Excel processing failed: {str(e)}")

    @staticmethod
    def create_final_shapefile(
        gdf: gpd.GeoDataFrame,
        df_summary: pd.DataFrame,
        spk_number: str,
        work_dir: Path
    ) -> Path:
        try:
            # Merge GDF with summary
            gdf_final = gdf.merge(df_summary, on='Name', how='left')

            # Fill nulls in numeric columns
            for col in ("Height", "Route_Spacing", "Task_Flight_Speed"):
                if col in gdf_final.columns:
                    gdf_final[col] = gdf_final[col].ffill().bfill()

            # Truncate column names to 10 characters (shapefile limitation)
            truncate_map = {
                col: col[:10]
                for col in gdf_final.columns
                if col != 'geometry'
            }
            gdf_final = gdf_final.rename(columns=truncate_map)

            # Reorder so geometry is last
            final_cols = list(truncate_map.values()) + ['geometry']
            gdf_final = gdf_final[final_cols]

            # Create output directory
            out_dir = work_dir / "output"
            if out_dir.exists():
                shutil.rmtree(out_dir)
            out_dir.mkdir()

            # Write shapefile
            final_shp = out_dir / f"{spk_number}.shp"
            gdf_final.to_file(final_shp, driver="ESRI Shapefile")

            # Write CPG file for UTF-8 encoding
            with open(out_dir / f"{spk_number}.cpg", 'w', encoding='utf-8') as f:
                f.write('UTF-8')

            # Create ZIP
            zip_out = work_dir / "final_upload.zip"
            if zip_out.exists():
                zip_out.unlink()

            with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as zout:
                for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
                    p = final_shp.with_suffix(f'.{ext}')
                    if p.exists():
                        zout.write(p, p.name)

            return zip_out

        except Exception as e:
            raise FileProcessingError(f"Final shapefile creation failed: {str(e)}")

    @staticmethod
    def load_shapefile_from_zip(zip_path: Path, work_dir: Path) -> gpd.GeoDataFrame:
        try:
            extract_dir = work_dir / "extracted_shp"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir()

            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)

            shp_files = list(extract_dir.glob('*.shp'))
            if not shp_files:
                raise FileProcessingError("No shapefile found in the uploaded ZIP")

            return gpd.read_file(shp_files[0])

        except Exception as e:
            raise FileProcessingError(f"Failed to load shapefile from ZIP: {str(e)}")
