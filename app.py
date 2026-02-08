import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import plotly.express as px
import time

st.set_page_config(page_title="Sofia Address Analyzer", layout="wide")

st.title("Анализ на адреси – София и София-област")

uploaded_file = st.file_uploader(
    "Качи Excel файл с една колона 'Address'",
    type=["xlsx"]
)

REFERENCE_ADDRESS = "София, ул. Нишава 107"
geolocator = Nominatim(user_agent="sofia_address_app")

@st.cache_data
def geocode_address(address):
    try:
        location = geolocator.geocode(address, addressdetails=True, timeout=10)
        if location:
            return (
                location.latitude,
                location.longitude,
                location.raw.get("address", {})
            )
    except:
        return None
    return None

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if "Address" not in df.columns:
        st.error("Файлът трябва да има колона с име 'Address'")
        st.stop()

    st.info("Обработване на адресите… Това може да отнеме малко време.")

    ref_location = geolocator.geocode(REFERENCE_ADDRESS)
    ref_coords = (ref_location.latitude, ref_location.longitude)

    results = []

    for address in df["Address"]:
        geo = geocode_address(address)
        time.sleep(1)

        if geo:
            lat, lon, details = geo
            distance_km = geodesic(ref_coords, (lat, lon)).km

            district = (
                details.get("city_district")
                or details.get("suburb")
                or details.get("city")
                or details.get("municipality")
                or "Неопределен"
            )

            results.append({
                "Address": address,
                "District": district,
                "Distance_km": round(distance_km, 2),
                "Latitude": lat,
                "Longitude": lon
            })

    data = pd.DataFrame(results)

    st.success(f"Обработени адреси: {len(data)}")

    # --- MAP ---
    m = folium.Map(location=ref_coords, zoom_start=11)

    folium.Marker(
        ref_coords,
        tooltip="Референтна точка: ул. Нишава 107",
        icon=folium.Icon(color="red")
    ).add_to(m)

    for _, row in data.iterrows():
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=5,
            popup=f"{row['Address']}<br>{row['District']}<br>{row['Distance_km']} км",
            fill=True
        ).add_to(m)

    st.subheader("Карта на адресите")
    st_folium(m, width=1200)

    # --- TABLE ---
    st.subheader("Таблица с анализ")
    st.dataframe(data[["Address", "District", "Distance_km"]])

    # --- DISTANCE BUCKETS ---
    def distance_bucket(d):
        if d <= 3:
            return "до 3 км"
        elif d <= 7:
            return "3–7 км"
        else:
            return "над 7 км"

    data["Distance_Group"] = data["Distance_km"].apply(distance_bucket)

    # --- CHARTS ---
    st.subheader("Разпределение по райони")
    fig_district = px.bar(
        data.groupby("District").size().reset_index(name="Count"),
        x="District",
        y="Count"
    )
    st.plotly_chart(fig_district, use_container_width=True)

    st.subheader("Разпределение по дистанция")
    fig_distance = px.pie(
        data.groupby("Distance_Group").size().reset_index(name="Count"),
        names="Distance_Group",
        values="Count"
    )
    st.plotly_chart(fig_distance)

    # --- TEXT RECOMMENDATIONS ---
    st.subheader("Автоматични изводи")

    top_district = data["District"].value_counts().idxmax()
    top_distance = data["Distance_Group"].value_counts().idxmax()

    st.write(
        f"Най-голяма концентрация на адреси се наблюдава в район {top_district}."
    )
    st.write(
        f"Повечето адреси попадат в дистанционната група '{top_distance}' спрямо ул. Нишава 107."
    )
