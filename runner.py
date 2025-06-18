import streamlit as st
import zipfile
import shutil
from pathlib import Path
import pandas as pd
import geopandas as gpd
from openpyxl import load_workbook
import xml.etree.ElementTree as ET
from shapely.geometry import LineString
import datetime

# --- Page Configuration (must be first Streamlit command) ---
st.set_page_config(page_title="Flight-Zone Selector & Exporter")

# --- Cleanup any previous artifacts on every reload ---
WORK_DIR = Path("working")
if WORK_DIR.exists():
    shutil.rmtree(WORK_DIR)
WORK_DIR.mkdir()

FINAL_ZIP = Path("final_upload.zip")
if FINAL_ZIP.exists():
    FINAL_ZIP.unlink()

EDIT_ZIP = Path("zones_for_edit.zip")
if EDIT_ZIP.exists():
    EDIT_ZIP.unlink()

# --- Sidebar Inputs ---
st.sidebar.header("Upload & Settings")
zip_file = st.sidebar.file_uploader("1. Upload KML ZIP", type="zip")
excel_file = st.sidebar.file_uploader("2. Upload Excel", type=["xlsx","xlsm","xls"])
OUT_SPK = st.sidebar.text_input("3. SPK number")
OUT_KEYID = st.sidebar.text_input("4. KeyID")

# --- Utility: Parse and merge KML layers ---
def parse_kmls(folder: Path) -> gpd.GeoDataFrame:
    records = []
    for kml in folder.rglob('*.kml'):
        root = ET.parse(kml).getroot()
        for pm in root.findall('.//Placemark'):
            name = pm.findtext('name')
            data = {d.attrib['name']: d.findtext('value') for d in pm.findall('.//Data')}
            def to_f(val):
                try:
                    return float(val)
                except:
                    return 0.0
            coords = [tuple(map(float, pt.split(',')[:2]))
                      for pt in pm.findtext('.//coordinates','').split()]
            records.append({
                'Name': name,
                'Flight_Controller_ID': data.get('Flight Controller ID',''),
                'Height': to_f(data.get('Height')),
                'Task_Flight_Speed': to_f(data.get('Task Flight Speed')),
                'Task_Area': to_f(data.get('Task Area')),
                'geometry': LineString(coords)
            })
    return gpd.GeoDataFrame(records, crs='EPSG:4326')

# --- Step 5: Generate Shapefile ZIP for QGIS editing ---
if st.sidebar.button("5. Generate & Download Shapefile ZIP for QGIS Edit"):
    if not (zip_file and excel_file and OUT_SPK and OUT_KEYID):
        st.sidebar.error("Please provide all inputs before generating.")
    else:
        # save and extract KML zip
        ZIP_IN = WORK_DIR / "data.zip"
        with open(ZIP_IN, 'wb') as f:
            f.write(zip_file.getbuffer())
        with zipfile.ZipFile(ZIP_IN, 'r') as zin:
            zin.extractall(WORK_DIR)
        # parse and write shapefile
        merged = parse_kmls(WORK_DIR)
        shp_path = WORK_DIR / f"{OUT_SPK}_zones.shp"
        merged.to_file(shp_path, driver='ESRI Shapefile')
        # zip shapefile components
        edit_zip = WORK_DIR / "zones_for_edit.zip"
        with zipfile.ZipFile(edit_zip, 'w', zipfile.ZIP_DEFLATED) as z:
            for ext in ['shp','shx','dbf','prj','cpg']:
                p = shp_path.with_suffix(f'.{ext}')
                if p.exists():
                    z.write(p, p.name)
        st.sidebar.success("Shapefile ready for QGIS edit. Download below.")
        st.sidebar.download_button(
            "Download shapefile ZIP for QGIS",
            data=open(edit_zip,'rb').read(),
            file_name=edit_zip.name
        )

st.markdown("---")

# --- Step 6: Upload Edited Shapefile ZIP or Skip editing ---
st.header("6. Upload Edited Shapefile ZIP (or skip editing)")
edited_zip = st.file_uploader("Upload edited shapefile ZIP", type="zip")

# --- Shared pipeline: Excel edit, join, export, zip ---
def process_pipeline(merged):
    # prepare output folder
    OUT_DIR = WORK_DIR / "output"
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()
    # prepare Excel
    EXCEL_PATH = WORK_DIR / "data.xlsx"
    with open(EXCEL_PATH, 'wb') as f:
        f.write(excel_file.getbuffer())
    wb = load_workbook(EXCEL_PATH)
    sheet = wb['flight record']
    orig = [c.value for c in sheet['L']]
    sheet.insert_cols(1)
    for i, v in enumerate(orig, start=1):
        sheet.cell(row=i, column=1).value = v
    wb.save(EXCEL_PATH)
    df_f = pd.read_excel(EXCEL_PATH, sheet_name='flight record', engine='openpyxl')
    # filter merged to only zones present in flight record
    serial_col = df_f.columns[0]
    merged_filt = merged[merged['Name'].astype(str).isin(df_f[serial_col].astype(str))].reset_index(drop=True)
    # build Sheet1
    df1 = pd.DataFrame({'Name': merged_filt['Name']})
    def lookup(s, idx):
        sub = df_f[df_f[df_f.columns[0]] == s]
        return sub.iloc[0, idx] if not sub.empty else None
    df1['TaskAmount'] = df1['Name'].map(lambda s: (lookup(s,6) or 0) * 1000)
    df1['StarFlight'] = df1['Name'].map(lambda s: str(lookup(s,1) or '')[:19])
    df1['EndFlight']  = df1['Name'].map(lambda s: (lambda v: str(v)[:11] + str(v)[-8:])(lookup(s,1)))
    df1['Capacity']   = 25
    df1['SPKNumber']  = OUT_SPK
    df1['KeyID']      = OUT_KEYID
    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as w:
        df1.to_excel(w, sheet_name='Sheet1', index=False)
    # export final shapefile
    gdf = merged_filt.merge(df1, on='Name', how='left')
    final_shp = OUT_DIR / f"{OUT_SPK}.shp"


    export_cols = [
    "Name",
    "Flight_Controller_ID",
    "Height",
    "Task_Flight_Speed",
    "Task_Area",
    "TaskAmount",
    "StarFlight",
    "EndFlight",
    "Capacity",
    "SPKNumber",
    "KeyID",
    "geometry",
    ]
    gdf = gdf[export_cols]
    gdf.to_file(final_shp, driver="ESRI Shapefile")
    # write CPG
    with open(OUT_DIR / f"{OUT_SPK}.cpg", 'w', encoding='utf-8') as f:
        f.write('UTF-8')
    # zip final components
    ZIP_OUT = WORK_DIR / "final_upload.zip"
    if ZIP_OUT.exists():
        ZIP_OUT.unlink()
    with zipfile.ZipFile(ZIP_OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for ext in ['shp','shx','dbf','prj','cpg']:
            p = final_shp.with_suffix(f'.{ext}')
            if p.exists():
                zout.write(p, p.name)
    st.write("▶︎ Columns in the final GDF:", gdf.columns.tolist())
    # --- Display final output as a table ---
    st.write("**Final Export Data:**")
    st.dataframe(gdf[['Name', 'Flight_Controller_ID', 'Height', 'Task_Flight_Speed', 'Task_Area', 'TaskAmount', 'StarFlight', 'EndFlight', 'Capacity', 'SPKNumber', 'KeyID']].head(10))
    # --- Provide download link for final ZIP ---
    st.success("✅ Final ZIP ready for download.")
    st.download_button(
        "Download Final Upload ZIP",
        data=open(ZIP_OUT,'rb').read(),
        file_name=ZIP_OUT.name
    )


# --- Execute pipeline based on user action ---
if edited_zip:
    # extract into fresh folder
    EDIT_DIR = WORK_DIR / "edited_shp"
    if EDIT_DIR.exists():
        shutil.rmtree(EDIT_DIR)
    EDIT_DIR.mkdir()
    temp_zip = EDIT_DIR / "edited.zip"
    with open(temp_zip, 'wb') as f:
        f.write(edited_zip.getbuffer())
    with zipfile.ZipFile(temp_zip, 'r') as zin:
        zin.extractall(EDIT_DIR)
    # load first shapefile found
    shp_list = list(EDIT_DIR.glob('*.shp'))
    if not shp_list:
        st.error(f"No shapefile found in edited folder {EDIT_DIR}")
    else:
        shp_temp = shp_list[0]
        merged = gpd.read_file(shp_temp)
        st.write("**Edited Zones Loaded:**", merged[['Name','Task_Area']])
        process_pipeline(merged)
elif st.sidebar.button("Skip edit and generate final ZIP"):
    # parse original KMLs
    ZIP_IN = WORK_DIR / "data.zip"
    with open(ZIP_IN, 'wb') as f:
        f.write(zip_file.getbuffer())
    with zipfile.ZipFile(ZIP_IN, 'r') as zin:
        zin.extractall(WORK_DIR)
    merged = parse_kmls(WORK_DIR)
    process_pipeline(merged)

# --- Footer / Watermark (fixed at bottom) ---
year = datetime.date.today().year
footer_html = f"""
<style>
.footer {{
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    text-align: center;
    color: #888;
    font-size: 0.8rem;
    padding: 0.5rem 0;
    background-color: rgba(255,255,255,0.9);
    z-index: 1000;
}}
</style>
<div class="footer">© {year} Radinal Dewantara Husein</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)