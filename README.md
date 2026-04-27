# 🎖️ OPERATION IRONSHIELD

**Microsoft Fabric Real-Time Intelligence — symulacja pola walki**

Demo end-to-end pokazujące możliwości **Microsoft Fabric Real-Time Intelligence**
(Eventstream → Eventhouse / KQL → Real-Time Dashboard → Data Agents + Operations
Agents → Power Automate → Teams) w realistycznym scenariuszu wojskowym
osadzonym na Poligonie Drawsko Pomorskie.

> ⚠️ **Disclaimer** — całość jest fikcją technologiczną stworzoną w celach
> edukacyjnych i demonstracyjnych. Wszystkie dane są generowane proceduralnie
> (`generate_datasets.py`, `random.seed(42)`).

---

## 🏗️ Architektura

![Architektura OPERATION IRONSHIELD](IRONSHIELD%20architecture.png)

Pełny diagram źródłowy w Mermaid: [`architecture.mmd`](architecture.mmd)
Prompt do regeneracji obrazu: [`ARCHITECTURE_IMAGE_PROMPT.md`](ARCHITECTURE_IMAGE_PROMPT.md)

### 7 źródeł danych (symulowane sensory)

| Strumień | Plik | Opis |
|---|---|---|
| 🛰️ Radary | `radar_detections.jsonl` | Wykrycia radarowe (Blue/Hostile/Unknown tracks) |
| 🚁 Drony | `drone_observations.jsonl` | Obserwacje wizyjne z dronów ISR |
| 🚛 Pojazdy | `vehicle_status.jsonl` | Telemetria pojazdów (paliwo, lokalizacja, status) |
| 🪖 Żołnierze | `soldier_health.jsonl` | Biometria (HR, SpO2, lokalizacja) |
| 🌦️ Pogoda | `weather_data.jsonl` | Dane meteorologiczne sektorów |
| 📡 SIGINT | `sigint_intercepts.jsonl` | Przechwycone sygnały radiowe |
| 📦 Logistyka | `ammo_logistics.jsonl` | Stan amunicji i zaopatrzenia |

---

## 📁 Struktura repozytorium

```
fabric-military-demo/
├── README.md                          # Ten plik
├── LICENSE                            # MIT
├── architecture.mmd                   # Diagram architektury (Mermaid)
├── ARCHITECTURE_IMAGE_PROMPT.md       # Prompt do generowania obrazu architektury
├── IRONSHIELD architecture.png        # Wyrenderowany diagram
├── IRONSHIELD_Scenario_Demo.docx      # Pełny scenariusz demo (Word)
├── IRONSHIELD_Scenario_Demo.pptx      # Slajdy do prezentacji
├── IRONSHIELD_Setup_Guide_v2.docx     # Krok-po-kroku setup w Fabric (najnowsza)
├── IRONSHIELD_Setup_Guide.docx        # Wcześniejsza wersja setup guide
│
├── generate_datasets.py               # Generator 7 strumieni JSONL (seed=42)
├── generate_ironshield.py             # Generator dokumentu .docx scenariusza
├── generate_guide.py                  # Generator setup guide .docx
│
└── datasets/
    ├── radar_detections.jsonl         # 7 plików JSONL z danymi
    ├── drone_observations.jsonl
    ├── vehicle_status.jsonl
    ├── soldier_health.jsonl
    ├── weather_data.jsonl
    ├── sigint_intercepts.jsonl
    ├── ammo_logistics.jsonl
    ├── _all_events_combined.json      # Zagregowany podgląd
    ├── eventhouse_kql_setup.kql       # KQL: tabele + Update Policies
    ├── dashboard_queries.kql          # KQL: zapytania do dashboardu
    └── fabric_notebook_sender.py      # Notebook Fabric → Event Hub SDK
```

---

## 🚀 Szybki start

### 1. Sklonuj repo

```bash
git clone https://github.com/llyen/fabric-military-demo.git
cd fabric-military-demo
```

### 2. (Opcjonalnie) Zregeneruj datasety

Wszystkie pliki w `datasets/*.jsonl` są deterministyczne (seed=42).
Aby je odtworzyć:

```bash
pip install python-docx python-pptx
python generate_datasets.py
```

### 3. Setup w Microsoft Fabric

Pełna instrukcja krok-po-kroku znajduje się w **`IRONSHIELD_Setup_Guide_v2.docx`**.

W skrócie:

1. **Utwórz Workspace** w Microsoft Fabric (z capacity F2+).
2. **Lakehouse** `IRONSHIELD_Lakehouse` → wgraj 7 plików JSONL z `datasets/`.
3. **Eventhouse** → KQL Database → uruchom `datasets/eventhouse_kql_setup.kql`
   (tworzy tabelę `RawEvents` + 7 typowanych tabel + Update Policies).
4. **Eventstream** → źródło **Custom App** → skopiuj connection string.
5. **Azure Event Hub** (lub Custom App endpoint) → uruchom notebook
   `datasets/fabric_notebook_sender.py` jako Fabric Notebook.
6. **Real-Time Dashboard** → użyj zapytań z `datasets/dashboard_queries.kql`.
7. **Data Agents** (3): Intel, Supply, Medic — patrz scenariusz w docx.
8. **Operations Agents / Activator** (4): Threat Response, Logistics, MEDEVAC, EW.
9. **Power Automate + Teams** — Adaptive Cards z human-in-the-loop.

---

## 🤖 Agenci AI w demie

### Data Agents (NL → KQL → odpowiedź)

| Agent | Źródła KQL | Przykładowe pytanie |
|---|---|---|
| 🎖️ **IRONSHIELD Intel** | RadarDetections + DroneObservations + SigintIntercepts | *„Ile hostile tracks w sektorze Bravo w ostatniej godzinie?"* |
| 📦 **IRONSHIELD Supply** | AmmoLogistics + VehicleStatus + WeatherData | *„Które pojazdy mają paliwo poniżej 30%?"* |
| 🩺 **IRONSHIELD Medic** | SoldierHealth + VehicleStatus | *„Wskaż żołnierzy z HR > 180 w ostatnich 5 minutach."* |

### Operations Agents / Activator (observe → analyze → decide → act)

| Agent | Trigger | Akcja |
|---|---|---|
| 🚨 Threat Response | Hostile contacts > próg | Power Automate → Teams (Adaptive Card) |
| 📦 Logistics Optimizer | Ammo/fuel < 30% | Approval workflow w Teams |
| 🚑 MEDEVAC Alert | HR > 200 lub SpO2 < 90 | Pilny alert na kanał OPS |
| 📡 EW Response | Anomalia w SIGINT | Notyfikacja do EW cell |

---

## 🛡️ Disclaimer

Projekt służy wyłącznie celom **edukacyjnym i demonstracyjnym** możliwości
Microsoft Fabric Real-Time Intelligence. Wszystkie dane, jednostki, lokalizacje
i scenariusze są **fikcyjne i wygenerowane proceduralnie**. Nie reprezentują
rzeczywistych operacji wojskowych ani zdolności żadnej organizacji.

---

## 📜 Licencja

[MIT](LICENSE)
