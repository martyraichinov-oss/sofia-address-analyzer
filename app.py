import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import plotly.express as px
import time

# -------------------------------------------------
# ОСНОВНИ НАСТРОЙКИ
# -------------------------------------------------
st.set_page_config(page_title="Sofia Address Analyzer", layout="wide")
st.title("Анализ на адреси – София и София-област")

# -------------------------------------------------
# РЕФЕРЕНТНА ТОЧКА (ФИКСИРАНА)
# -------------------------------------------------
ref_coords = (42.68333, 23.29167)  # ул. Нишава 107

geolocator = Nominatim(user_agent="sofia_address_app")

# -------------------------------------------------
# КАЧВАНЕ НА ФАЙЛ
# -------------------------------------------------
uploaded_file = st.file_uploader(
    "Качи Excel файл с една колона с име 'Address'",
    type=["xlsx"]
)

# -------------------------------------------------
# ГЕОКОДИНГ ФУНКЦИЯ (ЗАКЛЮЧЕНА В СОФИЯ)
# -------------------------------------------------
def geocode_address(address):
    try:
        clean_address = address.strip().strip(",")

        location = geolocator.geocode(
            clean_address,
            addressdetails=True,
            timeout=10,
            country_codes="bg",
            viewbox="23.10,42.55,23.45,42.80",
            bounded=True
        )

        if location:
            return (
                location.latitude,
                location.longitude,
                location.raw.get("address", {})
            )
    except Exception:
        return None

    return None

# -------------------------------------------------
# ОСНОВНА ЛОГИКА
# -------------------------------------------------
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if "Address" not in df.columns:
        st.error("Excel файлът трябва да съдържа колона с име 'Address'")
        st.stop()

    st.info("Обработване на адресите… Моля, изчакай.")

    results = []

    for address in df["Address"]:
        geo = geocode_address(address)
        time.sleep(1.5)

        if not geo:
            st.write("⚠️ Адресът не можа да бъде геокодиран:", address)
            continue

        lat, lon, details = geo
        distance_km = geodesic(ref_coords, (lat, lon)).km

        if distance_km > 15:
            st.write("⚠️ Адресът е извън допустимата дистанция:", address)
            continue

        district = (
            details.get("city_district")
            or details.get("suburb")
            or details.get("municipality")
            or details.get("city")
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

    if data.empty:
        st.warning("Нито един адрес не можа да бъде коректно позициониран.")
        st.stop()

    st.success(f"Успешно визуализирани адреси: {len(data)}")

    # -------------------------------------------------
    # КАРТА
    # -------------------------------------------------
    st.subheader("Карта на адресите")

    m = folium.Map(location=ref_coords, zoom_start=11)

    folium.Marker(
        ref_coords,
        tooltip="Референтна точка: ул. Нишава 107",
        icon=folium.Icon(color="red")
    ).add_to(m)

    for _, row in data.iterrows():
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6,
            popup=f"{row['Address']}<br>{row['District']}<br>{row['Distance_km']} км",
            fill=True
        ).add_to(m)

    st_folium(m, width=1200)

    # -------------------------------------------------
    # ТАБЛИЦА
    # -------------------------------------------------
    st.subheader("Таблица с адреси")
    st.dataframe(data[["Address", "District", "Distance_km"]])

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

    data["Distance_Group"] = data["Distance_km"].apply(distance_bucket)

    # -------------------------------------------------
    # ГРАФИКИ
    # -------------------------------------------------
    st.subheader("Разпределение по райони")
    fig_district = px.bar(
        data.groupby("District").size().reset_index(name="Брой"),
        x="District",
        y="Брой"
    )
    st.plotly_chart(fig_district, use_container_width=True)

    st.subheader("Разпределение по дистанция")
    fig_distance = px.pie(
        data.groupby("Distance_Group").size().reset_index(name="Брой"),
        names="Distance_Group",
        values="Брой"
    )
    st.plotly_chart(fig_distance)

    # -------------------------------------------------
    # ТЕКСТОВИ ИЗВОДИ
    # -------------------------------------------------
    st.subheader("Автоматични текстови изводи")

    top_district = data["District"].value_counts().idxmax()
    top_distance = data["Distance_Group"].value_counts().idxmax()

    st.write(f"Най-голяма концентрация се наблюдава в район {top_district}.")
    st.write(
        f"По-голямата част от адресите са на дистанция '{top_distance}' спрямо ул. Нишава 107."
    )
