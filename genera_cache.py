import json
from datetime import datetime

# Simulazione base: aggiungi qui dati reali nel tuo formato
camere_ultime_foto = {
    "Reo 100 Tecnisa Kalea": {
        "timestamp": datetime.now().isoformat(),
        "path": "/REO_100/2025/07/24",
        "filename": "Reo 100 Tecnisa Kalea_00_20250724120000.jpg"
    },
    "Reo 124 Telmec": {
        "timestamp": datetime.now().isoformat(),
        "path": "/REO_124/2025/07/23",
        "filename": "Reo 124 Telmec_00_20250723110000.jpg"
    }
}

with open("cache_ultime_foto.json", "w") as f:
    json.dump(camere_ultime_foto, f, indent=2)

print("✅ Cache generata correttamente.")

