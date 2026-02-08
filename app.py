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

REFERENCE_ADDRESS = "София, ул. Нишава 107"

# -------------------------------------------------
# ГЕОКОДИНГ – РЕФЕРЕНТНА ТОЧКА (СТАБИЛНА)
# -------------------------------------------------
geolocator = Nominatim(user_agent="sofia_address_app")

ref_location = geolocator.geocode(REFERENCE_ADDRESS, timeout=10)
if not ref_location:
    st.error(
        "Референтният адрес (ул. Нишава 107) не може да бъде намерен в момента. "
        "Моля, опитай отново след малко."
    )
    st.stop()

ref_coords = (ref_location.latitude, ref_location.longitude)

# -------------------------------------------------
# КАЧВАНЕ НА ФАЙЛ
# -------------------------------------------------
uploaded_file = st.file_uploader(
    "Качи Excel файл с една колона с име 'Address'",
    type=["xlsx"]
)

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
        time.sleep(1)  # важно за безплатния геокодинг

        if geo:
            lat, lon, details = geo
            distance_km = geodesic(ref_coords, (lat, lon)).km

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
        st.warning("Нито един адрес не можа да бъде разпознат.")
        st.stop()

    st.success(f"Успешно обработени адреси: {len(data)}")

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
            radius=5,
            popup=f"{row['Address']}<br>{row['District']}<br>{row['Distance_km']} км",
            fill=True
        ).add_to(m)

    st_folium(m, width=1200)

    # -------------------------------------------------
    # ТАБЛИЦА
    # -------------------------------------------------
    st.subheader("Таблица с адреси, райони и дистанция")
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
    st.subheader("Разпределение по административни райони")

    district_chart = (
        data.groupby("District")
        .size()
        .reset_index(name="Брой")
    )

    fig_district = px.bar(
        district_chart,
        x="District",
        y="Брой"
    )
    st.plotly_chart(fig_district, use_container_width=True)

    st.subheader("Разпределение по дистанция")

    distance_chart = (
        data.groupby("Distance_Group")
        .size()
        .reset_index(name="Брой")
    )

    fig_distance = px.pie(
        distance_chart,
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

    st.write(
        f"Най-голяма концентрация на адреси се наблюдава в район {top_district}."
    )
    st.write(
        f"По-голямата част от адресите се намират на дистанция '{top_distance}' спрямо ул. Нишава 107."
    )
