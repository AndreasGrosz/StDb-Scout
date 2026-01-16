I've created a visualization tool for you to check the digitized patterns. When you finish testing the CLI digitizer, you can use this to see what the extracted curves look like:

  Usage:

  # Plot all diagrams from ODS
  python tools/plot_pattern_from_ods.py Stdb_patterns.ods

  # Plot only specific antenna/frequency/polarization
  python tools/plot_pattern_from_ods.py Stdb_patterns.ods --antenna AIR3268 --freq 738-921 --hv h
  python tools/plot_pattern_from_ods.py msi-files/Stdb_patterns_v2.ods --antenna AIR3268


  Features:
  - Shows digitized curve as polar diagram
  - Overlays grid circles (3dB, 10dB, 20dB) for reference
  - Shows 30° sector lines
  - Saves PNG images: pattern_AIR3268_738-921_h.png
  - Reports quality metrics (mean, median, maximum jumps)
  - Warns if large jumps detected (>5 dB)

  Output includes:
  - Visual polar diagram with correct orientation (0° = North)
  - Statistics: mean/median attenuation, max jumps
  - Quality warnings if curve has issues

  This will help you verify that the grid filtering and median smoothing worked correctly. The diagrams should now show smooth curves without jumps at grid circle positions.

  Let me know how the testing goes and if you see any issues with the digitized patterns!

