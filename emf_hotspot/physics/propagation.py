"""
Physikalische Berechnungen für elektromagnetische Feldstärke
"""

import numpy as np

from ..config import MIN_DISTANCE_M, E_FIELD_CONSTANT


def e_field_free_space(erp_watts: float, distance_m: float) -> float:
    """
    Berechnet E-Feldstärke im Freiraum (ohne Dämpfung).

    Formel: E = sqrt(K * ERP) / d

    Schweizer NISV-Praxis: K = 49 (validiert mit offiziellen StdB)
    International Standard: K = 30

    Herleitung Standard (K=30):
    - Leistungsdichte S = ERP / (4 * pi * d²)
    - E² = S * Z0 = S * 120 * pi
    - E² = ERP * 30 / d²
    - E = sqrt(30 * ERP) / d

    Args:
        erp_watts: Equivalent Radiated Power [W]
        distance_m: Abstand [m]

    Returns:
        E-Feldstärke [V/m]
    """
    if distance_m < MIN_DISTANCE_M:
        distance_m = MIN_DISTANCE_M

    if erp_watts <= 0:
        return 0.0

    return np.sqrt(E_FIELD_CONSTANT * erp_watts) / distance_m


def apply_attenuation(e_field: float, attenuation_db: float) -> float:
    """
    Wendet Dämpfung in dB auf E-Feldstärke an.

    Korrekte Formel für Feldgrößen: E_out = E_in * 10^(-dB/20)

    Dies entspricht auch Excel/BAFU, wo gamma = 10^(dB/10) unter sqrt() steht:
    E = ... * sqrt(1/gamma) = ... * 10^(-dB/20)

    Args:
        e_field: E-Feldstärke [V/m]
        attenuation_db: Dämpfung [dB] (positiv = Abschwächung)

    Returns:
        Gedämpfte E-Feldstärke [V/m]
    """
    if attenuation_db <= 0:
        return e_field

    return e_field * 10.0 ** (-attenuation_db / 20.0)


def calculate_e_field_with_pattern(
    erp_watts: float,
    distance_m: float,
    h_attenuation_db: float,
    v_attenuation_db: float,
    building_attenuation_db: float = 0.0,
) -> float:
    """
    Berechnet E-Feldstärke mit Antennendiagramm und Gebäudedämpfung.

    Excel-Formel: E = sqrt(K * ERP / (gamma_h * gamma_v * gamma_bldg)) / d
    mit gamma = 10^(dB/10) und K = 49 (Schweizer NISV-Praxis)

    Diese Formel ist mathematisch äquivalent zu:
    E = sqrt(K * ERP) / d * 10^(-(dB_h + dB_v + dB_bldg) / 20)

    Aber wir verwenden Excel's Ansatz direkt für maximale Kompatibilität.

    Args:
        erp_watts: Equivalent Radiated Power [W]
        distance_m: Abstand [m]
        h_attenuation_db: Horizontaldämpfung aus Antennendiagramm [dB]
        v_attenuation_db: Vertikaldämpfung aus Antennendiagramm [dB]
        building_attenuation_db: Gebäudedämpfung [dB] (optional)

    Returns:
        E-Feldstärke [V/m]
    """
    if distance_m < MIN_DISTANCE_M:
        distance_m = MIN_DISTANCE_M

    if erp_watts <= 0:
        return 0.0

    # Dämpfungsfaktoren (gamma = 10^(dB/10))
    gamma_h = 10.0 ** (h_attenuation_db / 10.0) if h_attenuation_db > 0 else 1.0
    gamma_v = 10.0 ** (v_attenuation_db / 10.0) if v_attenuation_db > 0 else 1.0
    gamma_building = 10.0 ** (building_attenuation_db / 10.0) if building_attenuation_db > 0 else 1.0

    # Gesamt-Dämpfungsfaktor
    gamma_total = gamma_h * gamma_v * gamma_building

    # Excel-Formel: E = sqrt(K * ERP / gamma_total) / distance
    # = sqrt(49) * sqrt(ERP / gamma_total) / distance
    # = 7 * sqrt(ERP / gamma_total) / distance
    return np.sqrt(E_FIELD_CONSTANT * erp_watts / gamma_total) / distance_m


def power_density_from_e_field(e_field_vm: float) -> float:
    """
    Berechnet Leistungsdichte aus E-Feldstärke.

    S = E² / Z0 = E² / 377 [W/m²]

    Args:
        e_field_vm: E-Feldstärke [V/m]

    Returns:
        Leistungsdichte [W/m²]
    """
    return e_field_vm**2 / 377.0


def e_field_from_power_density(power_density_wm2: float) -> float:
    """
    Berechnet E-Feldstärke aus Leistungsdichte.

    E = sqrt(S * Z0) = sqrt(S * 377) [V/m]

    Args:
        power_density_wm2: Leistungsdichte [W/m²]

    Returns:
        E-Feldstärke [V/m]
    """
    if power_density_wm2 <= 0:
        return 0.0
    return np.sqrt(power_density_wm2 * 377.0)
