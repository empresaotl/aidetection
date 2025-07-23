import streamlit as st
from datetime import datetime, timedelta

# Simulazione di una telecamera
cameras = {
    "Cam_01": datetime.now() - timedelta(hours=5),
    "Cam_02": datetime.now() - timedelta(hours=13),
    "Cam_03": datetime.now() - timedelta(days=1),
}

st.title("🔧 Pannello Amministratore - Stato Telecamere")

for cam_name, last_time in cameras.items():
    hours_passed = (datetime.now() - last_time).total_seconds() / 3600
    color = "🟢" if hours_passed < 12 else "🔴"
    st.write(f"{color} **{cam_name}** - Ultima foto: {last_time.strftime('%Y-%m-%d %H:%M:%S')} ({int(hours_passed)}h fa)")
