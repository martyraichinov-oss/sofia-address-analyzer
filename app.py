import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import plotly.express as px

# -------------------------------------------------
# НАСТРОЙКИ
# -------------------------------------------------
st.set_page_config(page_title="Анализ на адреси – София", layout="wide")
st.title("Анализ на адреси – София и София-област")

REF_COORDS = (42.68333, 23.29167)  # ул. Нишава 107

# -------------------------------------------------
# КАЧВАНЕ НА ФАЙЛ
# -------------------------------------------------
uploaded_file = st.file_uploader(
    "Качи Excel файл с готови координати",
    type=["xlsx"]
)

if not uploaded_file:
    st.info("Моля, качи файла с геокодирани адреси.")
    st.stop()

df = pd.read_excel(uploaded_file)

required_cols = {"Address", "Latitude", "Longitude"}
if not required_cols.issubset(df.columns):
    st.error("Файлът трябва да съдържа колони: Address, Latitude, Longitude")
    st.stop()

# -------------------------------------------------
# ПРЕСМЯТАНЕ НА ДИСТАНЦИЯ (ако липсва)
# -------------------------------------------------
if "Distance_km" not in df.columns:
    df["Distance_km"] = df.apply(
        lambda r: round(
            geodesic(REF_COORDS, (r["Latitude"], r["Longitude"])).km, 2
        ),
        axis=1
    )

# -------------------------------------------------
# ДИСТАНЦИОННИ ГРУПИ
# -------------------------------------------------
def distance_bucket(d):
    if d <= 3:
        return "до 3 км"
    elif d <= 7:
        return "3–7 км"
    else:
        return "над 7 км"

df["Distance_Group"] = df["Distance_km"].apply(distance_bucket)

# -------------------------------------------------
# КАРТА
# -------------------------------------------------
st.subheader("Карта на адресите")

m = folium.Map(location=REF_COORDS, zoom_start=11)

folium.Marker(
    REF_COORDS,
    tooltip="Референтна точка – ул. Нишава 107",
    icon=folium.Icon(color="red")
).add_to(m)

for _, r in df.iterrows():
    folium.CircleMarker(
        location=[r["Latitude"], r["Longitude"]],
        radius=6,
        popup=f"{r['Address']}<br>{r.get('District','')}<br>{r['Distance_km']} км",
        fill=True
    ).add_to(m)

st_folium(m, width=1200)

# -------------------------------------------------
# ТАБЛИЦА
# -------------------------------------------------
st.subheader("Таблица с адреси")
st.dataframe(
    df[["Address", "District", "Distance_km", "Distance_Group"]],
    use_container_width=True
)

# -------------------------------------------------
# ГРАФИКИ
# -------------------------------------------------
st.subheader("Разпределение по райони")
fig_district = px.bar(
    df.groupby("District").size().reset_index(name="Брой"),
    x="District",
    y="Брой"
)
st.plotly_chart(fig_district, use_container_width=True)

st.subheader("Разпределение по дистанция")
fig_distance = px.pie(
    df.groupby("Distance_Group").size().reset_index(name="Брой"),
    names="Distance_Group",
    values="Брой"
)
st.plotly_chart(fig_distance)

# -------------------------------------------------
# ТЕКСТОВИ ИЗВОДИ
# -------------------------------------------------
st.subheader("Автоматични текстови изводи")

top_district = df["District"].value_counts().idxmax()
top_distance = df["Distance_Group"].value_counts().idxmax()

st.write(f"Най-голяма концентрация на адреси се наблюдава в район {top_district}.")
st.write(
    f"По-голямата част от адресите са на дистанция '{top_distance}' спрямо ул. Нишава 107."
)
