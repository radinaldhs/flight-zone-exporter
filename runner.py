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

# ensure old zips removed
for f in ("final_upload.zip", "zones_for_edit.zip"):
    p = Path(f)
    if p.exists():
        p.unlink()

# --- Sidebar Inputs ---
st.sidebar.header("Upload & Settings")
zip_file   = st.sidebar.file_uploader("1. Upload KML ZIP", type="zip")
excel_file = st.sidebar.file_uploader("2. Upload Excel",    type=["xlsx","xlsm","xls"])
OUT_SPK    = st.sidebar.text_input("3. SPK number")
OUT_KEYID  = st.sidebar.text_input("4. KeyID")

# --- Utility: Parse and merge KML layers ---
def parse_kmls(folder: Path) -> gpd.GeoDataFrame:
    records = []
    for kml in folder.rglob("*.kml"):
        root = ET.parse(kml).getroot()
        for pm in root.findall(".//Placemark"):
            name = pm.findtext("name")
            data = {d.attrib["name"]: d.findtext("value") for d in pm.findall(".//Data")}
            def to_f(val):
                try: return float(val)
                except: return 0.0
            coords = [
                tuple(map(float, pt.split(",")[:2]))
                for pt in pm.findtext(".//coordinates","").split()
            ]
            records.append({
                "Name": name,
                "Flight_Controller_ID": data.get("Flight Controller ID",""),
                "Height": to_f(data.get("Height")),
                "Task_Flight_Speed": to_f(data.get("Task Flight Speed")),
                "Task_Area": to_f(data.get("Task Area")),
                "geometry": LineString(coords)
            })
    return gpd.GeoDataFrame(records, crs="EPSG:4326")

# --- Step 5: Generate Shapefile ZIP for QGIS editing ---
if st.sidebar.button("5. Generate & Download Shapefile ZIP for QGIS Edit"):
    if not (zip_file and excel_file and OUT_SPK and OUT_KEYID):
        st.sidebar.error("Please provide all inputs before generating.")
    else:
        # save & unpack KML ZIP
        ZIP_IN = WORK_DIR / "data.zip"
        with open(ZIP_IN, "wb") as f:
            f.write(zip_file.getbuffer())
        with zipfile.ZipFile(ZIP_IN, "r") as zin:
            zin.extractall(WORK_DIR)
        # parse & write shapefile
        merged = parse_kmls(WORK_DIR)
        shp_path = WORK_DIR / f"{OUT_SPK}_zones.shp"
        merged.to_file(shp_path, driver="ESRI Shapefile")
        # zip shapefile parts
        edit_zip = WORK_DIR / "zones_for_edit.zip"
        with zipfile.ZipFile(edit_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for ext in ("shp","shx","dbf","prj","cpg"):
                p = shp_path.with_suffix(f".{ext}")
                if p.exists(): z.write(p, p.name)
        st.sidebar.success("Shapefile ready for QGIS edit.")
        st.sidebar.download_button(
            "Download shapefile ZIP for QGIS",
            data=open(edit_zip,"rb").read(),
            file_name=edit_zip.name
        )

st.markdown("---")
st.header("6. Upload Edited Shapefile ZIP (or skip editing)")
edited_zip = st.file_uploader("Upload edited shapefile ZIP", type="zip")

# --- Shared pipeline: Excel edit, join, export, zip ---
def process_pipeline(merged: gpd.GeoDataFrame):
    # 1) Excel prep
    EXCEL_PATH = WORK_DIR / "data.xlsx"
    with open(EXCEL_PATH, "wb") as f:
        f.write(excel_file.getbuffer())
    wb = load_workbook(EXCEL_PATH)
    sheet = wb["flight record"]
    orig = [c.value for c in sheet["L"]]
    sheet.insert_cols(1)
    for i,v in enumerate(orig, start=1):
        sheet.cell(row=i, column=1).value = v
    wb.save(EXCEL_PATH)
    df_f = pd.read_excel(EXCEL_PATH, sheet_name="flight record", engine="openpyxl")

    # 2) filter only those Names present
    serial_col = df_f.columns[0]
    merged = merged[merged["Name"].astype(str)
                    .isin(df_f[serial_col].astype(str))].reset_index(drop=True)

    # 3) build Sheet1 DataFrame
    df1 = pd.DataFrame({"Name": merged["Name"]})
    def lookup(s, idx):
        sub = df_f[df_f[serial_col] == s]
        return sub.iloc[0, idx] if not sub.empty else None

    df1["TaskAmount"]      = df1["Name"].map(lambda s: (lookup(s,6) or 0)*1000)
    df1["StarFlight"]      = df1["Name"].map(lambda s: str(lookup(s,1) or "")[:19])
    df1["EndFlight"]       = df1["Name"].map(lambda s: (lambda v:str(v or "")[:11]+str(v or "")[-8:])(lookup(s,1)))
    df1["Capacity"]        = 25
    df1["SPKNumber"]       = OUT_SPK
    df1["KeyID"]           = OUT_KEYID

    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as w:
        df1.to_excel(w, sheet_name="Sheet1", index=False)

    # 4) join back to geometry
    gdf = merged.merge(df1, on="Name", how="left")

    # 🔍 inspect actual columns (debug)
    st.write("🔍 Raw shapefile columns:", gdf.columns.tolist())

    # 5) skip renaming—keep the original column names
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
        "geometry"
    ]    

    # 6) slice & wrap
    gdf = gpd.GeoDataFrame(
        gdf[export_cols],
        geometry="geometry",
        crs="EPSG:4326"
    )

    # 7) write out as GeoPackage instead of Shapefile
    OUT_DIR = WORK_DIR / "output"
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()

    # write a .gpkg with full field names preserved
    final_gpkg = OUT_DIR / f"{OUT_SPK}.gpkg"
    gdf.to_file(final_gpkg, driver="GPKG", layer="zones")

    # zip the .gpkg
    ZIP_OUT = WORK_DIR / "final_upload.zip"
    if ZIP_OUT.exists():
        ZIP_OUT.unlink()
    with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        zout.write(final_gpkg, final_gpkg.name)

    # 8) preview & download
    st.write("▶︎ Final columns:", gdf.columns.tolist())
    st.dataframe(gdf.drop(columns="geometry").head(10))
    st.success("✅ Final ZIP ready for download.")
    st.download_button(
        "Download Final Upload ZIP",
        data=open(ZIP_OUT,"rb").read(),
        file_name=ZIP_OUT.name
    )

# --- Execute pipeline based on user action ---
if edited_zip:
    # unpack into fresh subfolder
    EDIT_DIR = WORK_DIR / "edited_shp"
    if EDIT_DIR.exists(): shutil.rmtree(EDIT_DIR)
    EDIT_DIR.mkdir()
    tmp = EDIT_DIR / "edited.zip"
    tmp.write_bytes(edited_zip.getbuffer())
    with zipfile.ZipFile(tmp, "r") as zin:
        zin.extractall(EDIT_DIR)
    shp_list = list(EDIT_DIR.glob("*.shp"))
    if not shp_list:
        st.error("No .shp found in edited ZIP")
    else:
        merged = gpd.read_file(shp_list[0])
        st.write("**Edited Zones Loaded:**", merged[["Name","Task_Area"]])
        process_pipeline(merged)

elif st.sidebar.button("Skip edit and generate final ZIP"):
    # just reparse original KMLs
    ZIP_IN = WORK_DIR / "data.zip"
    with open(ZIP_IN, "wb") as f:
        f.write(zip_file.getbuffer())
    with zipfile.ZipFile(ZIP_IN, "r") as zin:
        zin.extractall(WORK_DIR)
    merged = parse_kmls(WORK_DIR)
    process_pipeline(merged)

# --- Footer / Watermark (fixed at bottom) ---
year = datetime.date.today().year
st.markdown(f"""
<style>
.footer {{
  position: fixed; left:0; bottom:0; width:100%;
  text-align:center; color:#888; font-size:0.8rem;
  background:rgba(255,255,255,0.9); padding:0.5em 0;
}}
</style>
<div class="footer">© {year} Radinal Dewantara Husein</div>
""", unsafe_allow_html=True)
