# OPERATION IRONSHIELD — Generowanie obrazu architektury

## Plik Mermaid
Schemat architektury: `architecture.mmd`

---

## Prompt do wygenerowania obrazu JPG

Poniżej prompt do użycia w narzędziu do generowania obrazów (np. DALL-E, Midjourney, 
Adobe Firefly, lub specjalistyczne narzędzie do diagramów architektonicznych):

---

### Prompt (EN — do generatora obrazów AI):

```
Create a professional military-themed system architecture diagram for "OPERATION IRONSHIELD" 
— a Microsoft Fabric Real-Time Intelligence battlefield simulation platform.

Visual style: Dark navy (#0B1D3A) background with olive green (#3D5A1E) and gold/amber 
(#C78C1E) accent colors. Clean, modern, technical blueprint aesthetic with subtle military 
grid overlay. Use sharp edges and clean iconography.

Layout (top-to-bottom data flow):

TOP LAYER — "BATTLEFIELD SENSORS" (7 sources in a horizontal row):
  Icons for: Radar, Drone, Vehicle, Soldier biometrics, Weather station, SIGINT antenna, 
  Ammo convoy. Each with a small streaming data indicator.

SECOND LAYER — "DATA PREPARATION":
  Python script (generate_datasets.py) → Lakehouse (JSONL storage) → Fabric Notebook 
  (sender). Show data flow arrows.

THIRD LAYER — "FABRIC REAL-TIME INTELLIGENCE" (large central block):
  Left: Eventstream (Custom App Source) — purple ingestion funnel
  Center: Eventhouse (KQL Database) with RawEvents table splitting via Update Policies 
  into 7 typed tables (RadarDetections, DroneObservations, VehicleStatus, SoldierHealth, 
  WeatherData, SigintIntercepts, AmmoLogistics)
  Right: Real-Time Dashboard with 7 tiles (map, charts, tables) auto-refreshing

FOURTH LAYER — "AI AGENTS" (two side-by-side groups inside the Fabric block):
  Left group "DATA AGENTS" (green tint): 3 agents — Intel, Supply, Medic. 
  NL → KQL conversation icons.
  Right group "OPERATIONS AGENTS / ACTIVATOR" (red tint): 4 agents — Threat Response, 
  Logistics Optimizer, MEDEVAC Alert, EW Response. Show observe→analyze→decide→act cycle.
  Label clearly: "Operations Agent / Activator (Reflex)" to indicate both options.

BOTTOM LAYER — "ACTIONS & INTEGRATION":
  Power Automate (flow icon) → Microsoft Teams (chat icon with Adaptive Card).
  Show human-in-the-loop approval flow.

BOTTOM CENTER — "COMMANDER" figure with gold highlight, connected to:
  - Data Agents (NL questions)
  - Dashboard (observation)
  - Teams (approval)

CROSS-CUTTING — Unity Catalog governance bar along the side.

Text: Use English labels. Title: "OPERATION IRONSHIELD — Microsoft Fabric Architecture".
Resolution: High (4K), landscape orientation, suitable for presentation slides.
No watermarks. Professional technical documentation quality.
```

---

### Alternatywa: Renderowanie Mermaid → JPG

Jeśli wolisz wyrenderować diagram Mermaid bezpośrednio:

1. **Mermaid Live Editor**: https://mermaid.live — wklej zawartość `architecture.mmd`, 
   eksportuj jako PNG/SVG
2. **mermaid-cli (mmdc)**:
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   mmdc -i architecture.mmd -o architecture.jpg -t dark -w 3200 -H 2400 -b "#0B1D3A"
   ```
3. **VS Code**: Extension "Mermaid Preview" → prawy klik → Export as PNG
4. **GitHub**: Mermaid jest renderowany natywnie w plikach .md na GitHubie

---

### Prompt (PL — skrócony, do opisu diagramu):

```
Schemat architektury systemu OPERATION IRONSHIELD opartego na Microsoft Fabric.
7 źródeł danych sensorycznych → Eventstream → Eventhouse (KQL) z Update Policies →
Real-Time Dashboard + 3 Data Agents (NL→KQL) + 4 Operations Agents/Activator 
(observe→analyze→decide→act) → Power Automate → Teams (human-in-the-loop).
Styl: wojskowy blueprint, ciemne tło, kolory navy/olive/gold.
```
