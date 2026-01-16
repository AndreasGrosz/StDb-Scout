Das simple_pattern_digitizer.py funktioniert nicht, weil OpenCV keine GUI-Unterstützung hat (kein GTK2). Nutze stattdessen das CLI-Tool:

  Verwendung: cli_pattern_digitizer.py

  python tools/cli_pattern_digitizer.py input/Stdb.pdf \
    -o msi-files/Stdb_patterns.ods \
    --start-page 32 \
    --stdb-id "ZAFE_Rev1.8"

  Workflow:

  1. Script konvertiert PDF → PNGs und zeigt den Pfad:
  → 40 Bilder erstellt in: /tmp/tmpXXXXXX
  2. Für jedes Diagramm:
    - Script fragt: Hat Seite 32 Diagramme? [j/n/fertig]:
    - Du antwortest: j (ja)
    - Script fragt: Wie viele Diagramme auf dieser Seite? [2]:
    - Du antwortest: 2 (oder ENTER für Default)
  3. Koordinaten eingeben:
    - Script zeigt: Bild: /tmp/tmpXXXXXX/page-32.png
    - Du öffnest das Bild in deinem Bildbetrachter (z.B. eog, gimp, gthumb)
    - Mit Maus-Cursor über Diagramm bewegen → Koordinaten ablesen
    - Script fragt: Mittelpunkt (x,y) oder 'skip':
    - Du gibst ein: 1234,1500 (Komma oder Leerzeichen)
    - Script fragt: Randpunkt (x,y):
    - Du gibst ein: 1234,2000
    - Script berechnet: → Radius: 500 px
  4. Metadaten:
    - Antennentyp: → SC3636
    - Frequenzband: → 2600
    - H oder V [h/v]: → h
  5. Nächstes Diagramm / Seite:
    - Wiederholt für Diagramm 2/2
    - Fragt dann: Hat Seite 33 Diagramme? [j/n/fertig]:
    - Bei fertig oder f stoppt die Kalibrierung
  6. Automatische Digitalisierung:
    - Script digitalisiert alle kalibrierten Diagramme
    - Exportiert nach ODS
    - Aktualisiert Registry

  Wichtige Parameter:

  - --start-page 32: Erste Seite mit Diagrammen (nach "Antenna Diagrams")
  - --stdb-id "ZAFE_Rev1.8": ID für die Quellen-Registry
  - --config patterns.json: Lade gespeicherte Kalibrierung (überspringt Eingabe)

  Bildbetrachter öffnen:

  # In neuem Terminal-Tab:
  eog /tmp/tmpXXXXXX/page-32.png
  # oder
  gthumb /tmp/tmpXXXXXX/
  # oder
  gimp /tmp/tmpXXXXXX/page-32.png

  In GIMP/Gthumb siehst du die Koordinaten wenn du mit der Maus über das Bild fährst (meist unten links in der Statusleiste).

  Probiere es aus - das Tool ist ready!

