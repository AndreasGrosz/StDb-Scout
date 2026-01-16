# Antennendiagramm-Quellen für EMF-Analysen

## 1. Internationale Datenbanken (Öffentlich zugänglich)

### ANFR (Frankreich) - Cartoradio
**Am vielversprechendsten für Europa!**

- **Web-Interface**: https://www.cartoradio.fr/
- **Suche**: Gehe zu "Rechercher" → Typ: "Support" → Technologie: "4G" oder "5G"
- **Antennen-Details**: Klicke auf Standort → Tab "Émetteurs" zeigt Antennentyp
- **Download**: Manche Standorte haben PDF-Links mit technischen Daten

**Direkte Suche für AIR3268:**
```
1. Gehe zu: https://www.cartoradio.fr/
2. Aktiviere Filter: Technologie = "4G/5G", Fréquence = "1800 MHz"
3. Klicke auf einen Standort in deiner Nähe
4. Tab "Émetteurs" → Suche nach "AIR" oder "Ericsson"
5. Unter "Documents" könnten MSI-Files oder Patterns sein
```

### FCC (USA) - Equipment Authorization

**Direkte Links:**
- **Suche AIR3268**: https://fccid.io/search.php?q=AIR3268
- **Ericsson allgemein**: https://fccid.io/search.php?q=Ericsson+Radio
- **Alternative FCC-Suche**: https://apps.fcc.gov/oetcf/eas/reports/SearchResults.cfm

**Wichtig**: Bei FCC nach "RF Exposure" oder "Test Reports" suchen - dort sind manchmal Antenna Patterns als Anhang.

### Europäische Telekom-Regulierer

**Deutschland - Bundesnetzagentur (BNetzA)**
- **EMF-Datenbank**: https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/EMF/start.html
- **Standortdatenbank**: https://www.emf3.bundesnetzagentur.de/karte/Default.aspx
- Meistens keine Patterns, aber Standort-Daten

**Österreich - RTR**
- https://www.senderkataster.at/

**UK - Ofcom**
- https://www.ofcom.org.uk/sitefinder

## 2. Hersteller-Quellen

### Ericsson AIR 3268

**Offizielle Produktseite:**
- https://www.ericsson.com/en/portfolio/networks/ericsson-radio-system/antenna-integrated-radio/air-3268

**Datenblätter (historisch):**
- Suche in Google: `"AIR 3268" filetype:pdf site:ericsson.com`
- Wayback Machine für alte Versionen: https://web.archive.org/

**Hinweis**: Seit ~2019 publiziert Ericsson keine Pattern-Diagramme mehr für adaptive Antennen (wegen Beamforming-Variabilität).

### Kathrein (jetzt Ericsson)
- https://www.kathrein.com/en/products/antennas/
- Viele ältere Patterns noch verfügbar

### CommScope / Andrew
- https://www.commscope.com/product-type/antennas/
- Produktsuche → "Technical Documents" → oft MSI-Files

### Huawei
- Öffentlich: https://carrier.huawei.com/en/products/wireless-network/5g
- Meistens keine Patterns öffentlich (wie du sagst: Mauern)

## 3. Wissenschaftliche/Akademische Quellen

### ResearchGate / IEEE Xplore
- Suche: "Ericsson AIR 3268 radiation pattern"
- Oft Messungen in Papers: https://www.researchgate.net/search/publication?q=antenna%20pattern%20AIR

### ITU (International Telecommunication Union)
- Recommendation ITU-R F.699: "Reference radiation patterns for fixed wireless system antennas"
- https://www.itu.int/rec/R-REC-F.699/en

### ETSI (European Telecommunications Standards Institute)
- https://www.etsi.org/standards-search
- Suche: "antenna pattern" oder "base station"

## 4. Schweizer Quellen (BGÖ-Anfrage)

### BAKOM (Bundesamt für Kommunikation)
**E-Mail-Vorlage:**
```
An: rechtsdienst@bakom.admin.ch
CC: info@bakom.admin.ch
Betreff: BGÖ-Anfrage: Antennendiagramme (MSI-Files) für EMF-Analysen

Sehr geehrte Damen und Herren

Gestützt auf das Öffentlichkeitsgesetz (BGÖ, SR 152.3, Art. 6) stelle ich
folgendes Gesuch um Zugang zu amtlichen Dokumenten:

1. MSI-Files oder Antennendiagramme (Horizontal/Vertikal) für Mobilfunk-
   antennen vom Typ Ericsson AIR 3268 (oder vergleichbare adaptive Antennen)

2. Technische Dokumentation zur Berechnungsmethodik für OMEN-Standort-
   datenblätter (insbesondere: Welche Pattern-Daten werden verwendet?)

3. Auskunft, welche Bundesstelle über diese Unterlagen verfügt, falls
   nicht das BAKOM (BAFU, ARE, etc.)

Begründung: Diese Daten sind notwendig für eine wissenschaftliche Analyse
der EMF-Immissionen im Kontext der NISV (SR 814.710). Die Nachvollziehbarkeit
behördlicher Berechnungen erfordert Zugang zu den zugrunde liegenden
technischen Parametern.

Ich bitte um Mitteilung innerhalb der gesetzlichen Frist (20 Tage, BGÖ Art. 13).
Falls Gebühren anfallen, bitte ich um vorgängige Information.

Freundliche Grüsse
[Dein Name]
[Adresse]
[E-Mail]
```

**Hinweis**: Falls BAKOM verweist auf BAFU → gleiche Anfrage an umwelt@bafu.admin.ch

### Kantonale Umweltämter
**Falls Verweigerung wegen "Betriebsgeheimnis":**

Argumentationshilfe:
- BGÖ Art. 7 Abs. 1: Geschäftsgeheimnisse sind geschützt
- ABER: Öffentliches Interesse an EMF-Transparenz überwiegt (BGÖ Art. 7 Abs. 2)
- Präzedenzfall: Deutschland/Frankreich publizieren diese Daten bereits
- Technische Parameter (dB-Werte) sind keine Geschäftsgeheimnisse

**Beschwerde-Instanz** (falls Verweigerung):
- Eidgenössischer Datenschutz- und Öffentlichkeitsbeauftragter (EDÖB)
- https://www.edoeb.admin.ch/
- Kostenlos, formlos per E-Mail

## 5. Alternative: Pattern-Modellierung

Falls keine MSI-Files verfügbar:

### Standard-Pattern für Sektorantennen (65°/7° Beamwidth)

**Azimut (Horizontal):**
```python
def azimuth_pattern_65deg(phi_deg):
    """Standardmodell für 65° Sektorantenne."""
    phi = np.deg2rad(phi_deg)
    Am = 25  # Max. Dämpfung
    phi_3dB = np.deg2rad(65)  # 3dB Beamwidth

    attenuation = -min(12 * (phi / phi_3dB)**2, Am)
    return attenuation  # in dB
```

**Elevation (Vertikal):**
```python
def elevation_pattern_7deg(theta_deg):
    """Standardmodell für 7° Elevation."""
    theta = np.deg2rad(theta_deg)
    theta_3dB = np.deg2rad(7)

    attenuation = -12 * (theta / theta_3dB)**2
    return max(attenuation, -30)  # Clip bei -30 dB
```

**Quelle**: ITU-R F.1336-5, Annex 1

## 6. Reverse Engineering aus OMEN-Daten

Falls dein StDB OMEN-Messpunkte mit **berechneten E-Feld-Werten** enthält:

```python
# Rückrechnung: E_calculated = f(ERP, Pattern, Distance)
# → Pattern = E_calculated * Distance / sqrt(30 * ERP)
```

Wenn du ~10 OMEN-Punkte hast, kannst du das Pattern rückrechnen.

## Zusammenfassung - Empfohlene Reihenfolge

1. **Sofort** (diese Woche):
   - [ ] ANFR Cartoradio durchsuchen (manuell, visuell)
   - [ ] FCC fccid.io nach "AIR3268" oder "Ericsson Radio"
   - [ ] BAKOM per E-Mail anfragen (BGÖ)

2. **Kurzfristig** (1-2 Wochen):
   - [ ] Falls keine MSI-Files: Standard-Modell verwenden (ITU-R F.1336)
   - [ ] H-Pattern digitalisieren (funktioniert), V-Pattern modellieren

3. **Mittelfristig** (1 Monat):
   - [ ] Falls BAKOM/BAFU verweigern: Beschwerde an EDÖB
   - [ ] Kontakt zu EMF-Forschungsgruppen (ETH, EPFL) - die haben oft Patterns

4. **Langfristig**:
   - [ ] Systematischer Aufbau einer Pattern-Bibliothek für CH-übliche Antennen

---

**Nächste Schritte:**
1. Kannst du die OMEN-Daten aus dem StDB extrahieren? → Reverse Engineering möglich
2. Soll ich die Standard-Pattern-Modelle (ITU-R) als Python-Funktionen implementieren?
3. Willst du die BAKOM-Anfrage jetzt abschicken, oder soll ich sie noch anpassen?
