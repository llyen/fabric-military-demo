# 🧰 Cheatsheet promptów — Copilot CLI dla Microsoft Fabric

Zestaw realnych promptów do skopiowania, które prowadzą agenta przez budowę
demo Fabric Real-Time Intelligence krok po kroku. Wzorowane na artefaktach
z `fabric-military-demo` (OPERATION IRONSHIELD).

> 💡 **Konwencja:** w komentarzach `[…]` podmień własną domenę
> (np. `[BRANŻA]`, `[SCENARIUSZ]`, `[REGION]`).

---

## 0️⃣ Setup sesji (raz na repo)

```text
Jesteśmy w pustym repo. Chcę zbudować end-to-end demo Microsoft Fabric
Real-Time Intelligence dla scenariusza: [SCENARIUSZ — np. monitoring floty
pojazdów dostawczych w aglomeracji warszawskiej].

Zanim zaczniesz cokolwiek pisać:
1. Użyj MCP MS Learn / MS Fabric żeby potwierdzić aktualną składnię:
   - .create table w Eventhouse,
   - Update Policies (.create-or-alter function + .alter table policy update),
   - Real-Time Dashboard query syntax.
2. Zaproponuj architekturę (źródła danych → Eventstream → Eventhouse → tabele
   typowane → Dashboard → agenci) jako bullet list. Czekaj na moje OK.
```

---

## 1️⃣ Generator datasetów zgodnych ze schematem

```text
Wygeneruj `generate_datasets.py`, który tworzy [N] strumieni JSONL w `./datasets/`
dla scenariusza [SCENARIUSZ]. Wymagania:

- `SEED = 42` na początku (deterministyczność).
- Geograficzny środek: [LAT, LON], promień [X] km, sektory nazwane
  Alpha/Bravo/Charlie/Delta z własnymi środkami.
- Timeline w fazach: Normal → Anomaly → Response → Recovery (po [M] minut każda).
- Spójne wymiary (np. ten sam VehicleId pojawia się w `vehicle_status` i
  `[inny_strumień]`).
- Każdy event: EventId (uuid4), Timestamp (UTC ISO8601), Sector, oraz pola
  specyficzne dla strumienia.
- Każdy plik JSONL — jeden event per linia.
- Skrypt ma być uruchamialny: `python generate_datasets.py`.

Po napisaniu uruchom go i pokaż mi `wc -l datasets/*.jsonl` oraz pierwszy
rekord każdego pliku.
```

### Wariant: wymuszenie narracji w danych

```text
Wzmocnij fazę Anomaly: w sektorze Bravo, między minutą 4 a 7, ma wystąpić
korelacja — wzrost [METRYKA_A] o 40% przy jednoczesnym spadku [METRYKA_B]
poniżej [PRÓG]. To ma być widoczne w dashboard query, nie szum statystyczny.
Zaktualizuj generator i uruchom ponownie.
```

---

## 2️⃣ Eventhouse: tabele + Update Policies

```text
Na podstawie schematów eventów z `generate_datasets.py` wygeneruj
`datasets/eventhouse_kql_setup.kql`:

1. `.create table RawEvents (Payload: dynamic, EnqueuedAt: datetime)` — landing.
2. Dla każdego strumienia: `.create table <Name> (…)` z silnym typowaniem
   (datetime, real, int, bool, string).
3. Dla każdego strumienia: `.create-or-alter function Extract<Name>()` która
   parsuje `RawEvents.Payload` (filtruje po `Payload.stream == "<name>"`)
   i mapuje pola.
4. `.alter table <Name> policy update` z `Source = RawEvents`,
   `Query = Extract<Name>()`, `IsEnabled = true`, `IsTransactional = false`.

Sprawdź w MCP MS Learn / MS Fabric, że składnia `.alter table policy update`
jest aktualna (zwłaszcza forma JSON policy). Dodaj komentarz `//` przy
każdej sekcji.
```

---

## 3️⃣ Dashboard queries

```text
Wygeneruj `datasets/dashboard_queries.kql` z zapytaniami pod kafelki
Real-Time Dashboard (auto-refresh 5s):

- 🗺️ Mapa operacyjna — wszystkie pojazdy + hostile tracks ostatnie 5 min.
- 📈 Trend [METRYKA] w czasie (1 min bins, ostatnia godzina).
- 🔴 Top 10 alertów (HR>200 lub SpO2<90) ostatnie 10 min.
- 📊 Heatmapa sektor × klasyfikacja, ostatnie 15 min.
- 📦 Stan logistyki — pojazdy z fuel<30% lub ammo<30%.

Każde zapytanie poprzedź komentarzem `// --- <Nazwa kafelka> ---`.
Trzymaj się limitów (`| take`, `| summarize`) żeby dashboard był responsywny.
```

---

## 4️⃣ Notebook Fabric — sender do Event Huba

```text
Wygeneruj `datasets/fabric_notebook_sender.py` jako kod do wklejenia w Fabric
Notebook (Spark). Wymagania:

- Czyta JSONL z `abfss://<ws>@onelake.dfs.fabric.microsoft.com/<lh>/Files/...`.
- Konfiguracja przez stałe na górze: EVENT_HUB_CONNECTION_STRING,
  LAKEHOUSE_PATH, TIME_SCALE (np. 0.5 = 2x szybciej niż real-time),
  TZ_OFFSET_HOURS (CET/CEST).
- Sortuje wszystkie eventy po Timestamp, wysyła w pętli z `time.sleep`
  odpowiadającym różnicy timestamp × TIME_SCALE.
- Używa `azure-eventhub` (`EventHubProducerClient`, `EventData`).
- Loguje co N eventów postęp.
- Na górze ma `# %pip install azure-eventhub --quiet`.
```

---

## 5️⃣ Data Agents i Operations Agents — opis konfiguracji

```text
Wygeneruj sekcję README opisującą [K] Data Agents (NL→KQL) i [L] Operations
Agents/Activator. Dla każdego:

- Nazwa + emoji.
- Źródła (które tabele Eventhouse).
- 3 przykładowe pytania w języku naturalnym (po polsku).
- Dla Operations Agents: trigger (warunek KQL) + akcja (Power Automate → Teams
  Adaptive Card, treść karty bullet pointami).

Zachowaj styl tabel z istniejącego README.
```

---

## 6️⃣ Diagram architektury (Mermaid + prompt do obrazu)

```text
Wygeneruj `architecture.mmd` w Mermaid (graph TB) pokazujący:
- Warstwę źródeł danych (sensory),
- Lakehouse + Notebook sender,
- Eventstream → Eventhouse (RawEvents + Update Policies + tabele typowane),
- Real-Time Dashboard,
- Data Agents i Operations Agents,
- Power Automate + Teams,
- Postać Dowódcy/Operatora z interakcjami.

Użyj kolorystyki: navy #0B1D3A, olive #3D5A1E, gold #C78C1E.
Dodaj classDef i przypisz klasy.

Następnie wygeneruj `ARCHITECTURE_IMAGE_PROMPT.md` — prompt po angielsku do
generatora obrazów (DALL-E/Midjourney) odzwierciedlający ten sam diagram
w stylu „military blueprint".
```

---

## 7️⃣ Dokumenty docx/pptx — scenariusz i setup guide

```text
Wygeneruj `generate_ironshield.py` (lub `generate_<scenariusz>.py`), który
używając `python-docx` i `python-pptx` tworzy:

- `[NAZWA]_Scenario_Demo.docx` — pełny scenariusz demo (role, timeline po
  minutach, dialogi prezenter↔dashboard, oczekiwane reakcje agentów AI).
- `[NAZWA]_Scenario_Demo.pptx` — 8-12 slajdów z architekturą i timeline'em.

Tekst po polsku, formatowanie z nagłówkami H1/H2, tabelami i bulletami.
Skrypt ma być re-runnable (nadpisuje pliki).

Po napisaniu uruchom: `pip install python-docx python-pptx && python generate_ironshield.py`.
```

Analogicznie dla setup guide:

```text
Wygeneruj `generate_guide.py` produkujący `[NAZWA]_Setup_Guide_v2.docx` —
krok-po-kroku instrukcję postawienia całości w Microsoft Fabric:
workspace (F2+) → Lakehouse → Eventhouse → Eventstream (Custom App) →
notebook sender → Dashboard → Data Agents → Operations Agents →
Power Automate → Teams. Każdy krok ze screenshotem-placeholderem
(`[Screenshot: …]`) i konkretnym przyciskiem do kliknięcia.
```

---

## 8️⃣ Iteracja — typowe drobne poprawki

```text
W `dashboard_queries.kql` w sekcji "Map tile: Hostile tracks" zmień kolor
klasyfikacji `Unknown` z czerwonego na żółty i dodaj `| take 500` dla
wydajności. Pokaż diff.
```

```text
W `generate_datasets.py` zwiększ intensywność `soldier_health` 2x w fazie
Engagement (więcej alertów HR>180). Reszta bez zmian. Po zmianie uruchom
generator i porównaj `wc -l` przed i po.
```

```text
Sprawdź w MCP MS Fabric, czy w Eventhouse można dziś (2026) używać
`materialized-view` dla agregacji 1-min hostile tracks per sektor.
Jeśli tak — dodaj definicję do `eventhouse_kql_setup.kql` i odpowiedni
kafelek do `dashboard_queries.kql`.
```

---

## 9️⃣ Weryfikacja zgodności z dokumentacją

```text
Przejrzyj `eventhouse_kql_setup.kql` i dla KAŻDEJ konstrukcji KQL
(`.create table`, `.create-or-alter function`, `.alter table … policy update`)
zacytuj w komentarzu link do strony MS Learn potwierdzającej składnię.
Użyj MCP MS Learn.
```

```text
Przejrzyj `fabric_notebook_sender.py` pod kątem best practices dla
`EventHubProducerClient`: batchowanie, retry policy, partition key.
Zaproponuj poprawki z uzasadnieniem (cytując MS Learn).
```

---

## 🔚 Zamykanie sesji

```text
Wygeneruj `README.md` dla całego repo: opis scenariusza, architektura
(z linkiem do .png i .mmd), struktura folderów, szybki start, opis agentów,
disclaimer (że to fikcja edukacyjna), licencja MIT.

Następnie zrób `git add -A && git status` i zaproponuj commit message
w stylu: `Initial commit: <NAZWA> - <jednolinijkowy opis>`.
```

---

## 📌 Złote zasady

1. **Każdy artefakt = skrypt.** Nie ręczne kopiowanie do portalu. Wszystko
   regenerowalne (`python …`, `.kql` w jednym pliku, `.mmd` w Mermaid).
2. **MCP MS Learn / MS Fabric to nie ozdoba.** Wymuszaj weryfikację składni
   KQL i SDK — to różnica między „działa" a „działało w wersji preview".
3. **Deterministyczność.** `SEED=42` w generatorach datasetów = powtarzalne
   demo, powtarzalne pytania do Data Agents, powtarzalne odpowiedzi.
4. **Narracja w danych.** Fazy scenariusza + wymuszone korelacje — żeby demo
   miało **historię**, nie tylko losowy szum.
5. **Dokumentacja jako kod.** `.docx`/`.pptx`/`.mmd` z generatorów = aktualne
   materiały w sekundę po każdej zmianie pipeline'u.
