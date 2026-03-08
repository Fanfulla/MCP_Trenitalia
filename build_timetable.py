#!/usr/bin/env python3
"""
Script one-shot: costruisce data/timetable.json.gz
Legge le 25.480 corse dal NeTEx, risolve fermate e orari di passaggio,
salva un indice compatto per le query offline.

Uso: python build_timetable.py
"""

import gzip
import json
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

NS = "http://www.netex.org.uk/netex"
NETEX_FILE = "IT-IT-TRENITALIA_L1.xml.gz"
OUT_FILE = Path("data/timetable.json.gz")

DAY_NAMES = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}


def parse_time(t: str | None) -> str:
    """Normalizza 'HH:MM:SS' → 'HH:MM', None → ''."""
    if not t:
        return ""
    return t[:5]


def main():
    print(f"Lettura {NETEX_FILE} (potrebbe richiedere ~1 minuto)...")
    with gzip.open(NETEX_FILE, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()

    # ── 1. Mappa ScheduledStopPoint ID → nome stazione ────────────────────────
    print("Costruzione mappa stazioni...")
    # StopAssignment: ScheduledStopPointRef → StopPlaceRef
    ssp_to_sp: dict[str, str] = {}
    for sa in root.findall(f".//{{{NS}}}PassengerStopAssignment"):
        ssp = sa.find(f"{{{NS}}}ScheduledStopPointRef")
        sp  = sa.find(f"{{{NS}}}StopPlaceRef")
        if ssp is not None and sp is not None:
            ssp_to_sp[ssp.get("ref", "")] = sp.get("ref", "")

    # StopPlace ref → nome
    sp_to_name: dict[str, str] = {}
    for sp in root.findall(f".//{{{NS}}}StopPlace"):
        name_el = sp.find(f"{{{NS}}}Name")
        if name_el is not None and name_el.text:
            sp_to_name[sp.get("id", "")] = name_el.text.strip().upper()

    def ssp_name(ssp_ref: str) -> str:
        return sp_to_name.get(ssp_to_sp.get(ssp_ref, ""), "")

    # ── 2. Mappa JourneyPattern ID → lista ordinata di SSP ref ───────────────
    print("Costruzione mappa journey patterns...")
    jp_stops: dict[str, list[str]] = {}
    for jp in root.findall(f".//{{{NS}}}ServiceJourneyPattern"):
        jpid = jp.get("id", "")
        pts = jp.find(f"{{{NS}}}pointsInSequence")
        if pts is None:
            continue
        refs = [el.get("ref", "") for el in pts.findall(f".//{{{NS}}}ScheduledStopPointRef")]
        jp_stops[jpid] = refs

    # ── 3. Linea per journey pattern ──────────────────────────────────────────
    jp_line: dict[str, str] = {}
    line_names: dict[str, str] = {}
    for line in root.findall(f".//{{{NS}}}Line"):
        lid = line.get("id", "")
        name_el = line.find(f"{{{NS}}}Name")
        if name_el is not None:
            line_names[lid] = name_el.text.strip()
    for jp in root.findall(f".//{{{NS}}}ServiceJourneyPattern"):
        jpid = jp.get("id", "")
        rv = jp.find(f"{{{NS}}}RouteView")
        if rv is not None:
            lr = rv.find(f"{{{NS}}}LineRef")
            if lr is not None:
                jp_line[jpid] = line_names.get(lr.get("ref", ""), "")

    # ── 4. DayType ID → {weekdays: set[int], from: date, to: date} ────────────
    print("Costruzione mappa day types...")
    dt_weekdays: dict[str, set[int]] = {}
    for dt in root.findall(f".//{{{NS}}}DayType"):
        dtid = dt.get("id", "")
        props = dt.find(f"{{{NS}}}properties")
        if props is None:
            continue
        days: set[int] = set()
        for prop in props:
            dow = prop.find(f"{{{NS}}}DaysOfWeek")
            if dow is not None and dow.text:
                for word in dow.text.split():
                    if word in DAY_NAMES:
                        days.add(DAY_NAMES[word])
        dt_weekdays[dtid] = days

    # DayTypeAssignment → OperatingPeriod ref per DayType
    dt_op: dict[str, str] = {}
    for dta in root.findall(f".//{{{NS}}}DayTypeAssignment"):
        dt_ref = dta.find(f"{{{NS}}}DayTypeRef")
        op_ref = dta.find(f"{{{NS}}}OperatingPeriodRef")
        if dt_ref is not None and op_ref is not None:
            dt_op[dt_ref.get("ref", "")] = op_ref.get("ref", "")

    # OperatingPeriod ID → (from_date, to_date)
    op_range: dict[str, tuple[str, str]] = {}
    for op in root.findall(f".//{{{NS}}}OperatingPeriod"):
        opid = op.get("id", "")
        fd = op.find(f"{{{NS}}}FromDate")
        td = op.find(f"{{{NS}}}ToDate")
        op_range[opid] = (
            (fd.text or "")[:10],
            (td.text or "")[:10],
        )

    # ── 5. Itera sui ServiceJourney e costruisce le entry ─────────────────────
    print("Elaborazione corse...")
    journeys = []
    vj_list = root.findall(f".//{{{NS}}}ServiceJourney")
    total = len(vj_list)

    for i, vj in enumerate(vj_list):
        if i % 2000 == 0:
            print(f"  {i}/{total}...")

        numero_el = vj.find(f"{{{NS}}}Name")
        numero = numero_el.text.strip() if numero_el is not None and numero_el.text else ""

        jp_ref_el = vj.find(f"{{{NS}}}ServiceJourneyPatternRef")
        jp_ref = jp_ref_el.get("ref", "") if jp_ref_el is not None else ""

        dt_ref_el = vj.find(f".//{{{NS}}}DayTypeRef")
        dt_ref = dt_ref_el.get("ref", "") if dt_ref_el is not None else ""

        passing_el = vj.find(f"{{{NS}}}passingTimes")
        if passing_el is None:
            continue

        # Orari di passaggio
        stop_times = []
        for tpt in passing_el.findall(f"{{{NS}}}TimetabledPassingTime"):
            arr = tpt.find(f"{{{NS}}}ArrivalTime")
            dep = tpt.find(f"{{{NS}}}DepartureTime")
            stop_times.append((
                parse_time(arr.text if arr is not None else None),
                parse_time(dep.text if dep is not None else None),
            ))

        # Fermate dal JourneyPattern
        ssp_refs = jp_stops.get(jp_ref, [])
        if len(ssp_refs) != len(stop_times):
            continue  # disallineamento — skip

        stops = []
        for ssp_ref, (arr, dep) in zip(ssp_refs, stop_times):
            name = ssp_name(ssp_ref)
            if name:
                stops.append([name, arr, dep])

        if not stops:
            continue

        # Day type info
        weekdays = dt_weekdays.get(dt_ref, set())
        op_ref = dt_op.get(dt_ref, "")
        period_from, period_to = op_range.get(op_ref, ("", ""))
        linea = jp_line.get(jp_ref, "")

        journeys.append({
            "n": numero,                        # numero treno
            "l": linea,                         # linea (Regionale, FR, ecc.)
            "w": sorted(weekdays),              # giorni della settimana (0=Mon, 6=Sun)
            "pf": period_from,                  # periodo da
            "pt": period_to,                    # periodo a
            "s": stops,                         # [[stazione, arrivo, partenza], ...]
        })

    print(f"\nCorse elaborate: {len(journeys)}/{total}")

    # ── 6. Salva compresso ────────────────────────────────────────────────────
    OUT_FILE.parent.mkdir(exist_ok=True)
    payload = json.dumps(journeys, ensure_ascii=False, separators=(",", ":"))
    with gzip.open(OUT_FILE, "wt", encoding="utf-8", compresslevel=9) as f:
        f.write(payload)

    size_mb = OUT_FILE.stat().st_size / 1024 / 1024
    print(f"Salvato in {OUT_FILE} ({size_mb:.1f} MB compressi, {len(journeys)} corse)")


if __name__ == "__main__":
    main()
