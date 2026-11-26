"""Controlador PyScript para la aplicación estática Integra."""

import asyncio
import base64
import html
import json
from datetime import date, datetime, timedelta
from io import BytesIO
from math import isfinite
import time
from urllib.parse import quote

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
    "font.size": 11,
    "axes.labelcolor": "#e2e8f0",
    "axes.edgecolor": "#334155",
    "axes.linewidth": 0.8,
    "axes.titlecolor": "#f8fafc",
    "axes.titlesize": 14,
    "xtick.color": "#cbd5e1",
    "ytick.color": "#cbd5e1",
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "grid.color": "#334155",
    "grid.linewidth": 0.7,
    "figure.facecolor": "#111827",
    "axes.facecolor": "#111827",
    "savefig.facecolor": "#111827",
    "savefig.dpi": 140,
})
import matplotlib.pyplot as plt
import numpy as np
from js import Blob, FileReader, URL, fetch, localStorage
from pyodide.ffi import create_proxy
from pyscript import document

from calculos import (
    calculate_corrosion,
    calculate_inspection_interval,
    calculate_pipe,
    calculate_rbi,
    calculate_tank,
    calculate_vessel,
)


STORAGE_KEY = "integra.project.v1"
EVENT_PROXIES = []
FAMILY_NAMES = {"pipe": "Tubería", "vessel": "Recipiente", "tank": "Tanque"}
STATUS_NAMES = {
    "normal": "Normal",
    "alert": "Alerta",
    "critical": "Espesor bajo el mínimo",
    "overdue": "Inspección vencida",
    "insufficient": "Datos insuficientes",
    "date_error": "Error de fechas",
    "no_corrosion": "CR ≤ 0 / advertencia",
    "error": "Error de cálculo",
}
FIELD_KEYS = [
    "design_pressure_mpa", "outside_diameter_mm", "inside_radius_mm",
    "allowable_stress_mpa", "weld_efficiency", "weld_strength_reduction",
    "coefficient_y", "tank_diameter_m", "liquid_height_m", "specific_gravity",
    "nominal_thickness_mm", "mill_tolerance_fraction", "corrosion_allowance_mm",
    "inspection_class_max_years",
]
SCHEMATICS = {
    "pipe": """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600" viewBox="0 0 1000 600" preserveAspectRatio="none">
<defs>
  <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#1e293b" stroke-width="1"/></pattern>
  <pattern id="major" width="100" height="100" patternUnits="userSpaceOnUse"><path d="M100 0H0V100" fill="none" stroke="#26364a" stroke-width="1.2"/></pattern>
  <linearGradient id="pipeMetal" x2="0" y2="1"><stop stop-color="#64748b" stop-opacity=".6"/><stop offset=".18" stop-color="#1e293b"/><stop offset=".52" stop-color="#334155" stop-opacity=".8"/><stop offset="1" stop-color="#0f172a"/></linearGradient>
  <marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0 0 9 4.5 0 9z" fill="#38bdf8"/></marker>
</defs>
<rect width="1000" height="600" fill="#0b1120"/><rect width="1000" height="600" fill="url(#grid)"/><rect width="1000" height="600" fill="url(#major)"/>
<rect x="18" y="18" width="964" height="564" rx="5" fill="none" stroke="#334155"/>
<text x="42" y="49" fill="#e2e8f0" font-size="17" font-family="Arial,sans-serif" font-weight="700" letter-spacing="2">P&amp;ID / ISOMÉTRICO · LÍNEA DE PROCESO</text>
<text x="42" y="73" fill="#94a3b8" font-size="12" font-family="Arial,sans-serif">ASME B31.3 · TRAMO RECTO · ELEVACIÓN NO A ESCALA</text>
<text x="836" y="48" fill="#38bdf8" font-size="13" font-family="Arial,sans-serif">LINE-100</text><text x="836" y="69" fill="#94a3b8" font-size="11" font-family="Arial,sans-serif">NPS 4 · ASTM A106 Gr. B</text>
<!-- dimension strings and pipe centerline -->
<path d="M145 145H855M145 137v17m710-17v17" fill="none" stroke="#cbd5e1" stroke-width="1.4"/><path d="m145 145 12-5v10zm710 0-12-5v10z" fill="#cbd5e1"/>
<text x="454" y="136" fill="#cbd5e1" font-size="13" font-family="Arial,sans-serif">TRAMO INSPECCIONABLE</text>
<path d="M82 300H920" fill="none" stroke="#38bdf8" stroke-width="1.4" stroke-dasharray="12 7 2 7"/>
<text x="81" y="286" fill="#38bdf8" font-size="11" font-family="Arial,sans-serif">EJE DE TUBERÍA</text>
<!-- process pipe and raised-face flanges -->
<rect x="115" y="252" width="770" height="96" rx="7" fill="url(#pipeMetal)" stroke="#38bdf8" stroke-width="2"/>
<path d="M121 261H879M121 339H879" stroke="#cbd5e1" stroke-opacity=".72" stroke-width="1.5"/>
<path d="M115 300H885" stroke="#38bdf8" stroke-width="1" stroke-dasharray="9 6"/>
<g fill="#0b1120" stroke="#cbd5e1" stroke-width="2">
  <rect x="135" y="241" width="19" height="118" rx="2"/><rect x="160" y="241" width="12" height="118" rx="2"/>
  <rect x="828" y="241" width="12" height="118" rx="2"/><rect x="851" y="241" width="19" height="118" rx="2"/>
</g>
<g fill="#38bdf8"><circle cx="144" cy="253" r="3"/><circle cx="144" cy="347" r="3"/><circle cx="160" cy="253" r="3"/><circle cx="160" cy="347" r="3"/><circle cx="837" cy="253" r="3"/><circle cx="837" cy="347" r="3"/><circle cx="860" cy="253" r="3"/><circle cx="860" cy="347" r="3"/></g>
<text x="108" y="382" fill="#94a3b8" font-size="10" font-family="Arial,sans-serif">BRIDA RF · 150#</text><text x="804" y="382" fill="#94a3b8" font-size="10" font-family="Arial,sans-serif">BRIDA RF · 150#</text>
<!-- circumferential welds -->
<g fill="none" stroke="#fbbf24" stroke-width="2"><path d="M320 252v96m5-96v96"/><path d="M684 252v96m5-96v96"/></g>
<text x="282" y="226" fill="#fbbf24" font-size="11" font-family="Arial,sans-serif">W-01 · SOLDADURA</text>
<text x="643" y="226" fill="#fbbf24" font-size="11" font-family="Arial,sans-serif">W-02 · SOLDADURA</text>
<!-- block valve, stem and handwheel -->
<path d="M452 253 474 275v50l-22 23m96-95-22 22v50l22 23m-96-73h96m-96 50h96" fill="#123347" fill-opacity=".92" stroke="#38bdf8" stroke-width="3"/>
<path d="M500 253v-48m0 0v-24" stroke="#cbd5e1" stroke-width="5"/>
<circle cx="500" cy="174" r="24" fill="none" stroke="#38bdf8" stroke-width="3"/>
<path d="M500 150v48m-24-24h48m-17-17-14 34m0-34 14 34" stroke="#cbd5e1" stroke-width="2"/>
<circle cx="500" cy="174" r="4" fill="#38bdf8"/>
<text x="454" y="408" fill="#e2e8f0" font-size="12" font-family="Arial,sans-serif">V-101 · VÁLVULA DE BLOQUEO</text>
<text x="482" y="424" fill="#94a3b8" font-size="10" font-family="Arial,sans-serif">COMPUERTA · VOLANTE</text>
<!-- flow arrows -->
<path d="M210 300h60m12 0h47m372 0h58" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrow)"/>
<text x="202" y="236" fill="#7dd3fc" font-size="11" font-family="Arial,sans-serif">TRAMO 1 · AGUAS ARRIBA</text>
<text x="706" y="236" fill="#7dd3fc" font-size="11" font-family="Arial,sans-serif">TRAMO 2</text>
<!-- rack support and shoe -->
<path d="M692 354h116l-12 22h-92z" fill="#334155" stroke="#cbd5e1" stroke-width="2"/>
<path d="M704 376v111m92-111v111m-112 0h132m-122-13h112" fill="none" stroke="#38bdf8" stroke-width="4"/>
<path d="M690 423h124M701 447h103" stroke="#64748b" stroke-width="2"/>
<path d="M681 500H825" stroke="#cbd5e1" stroke-width="2"/><path d="M699 500v10m108-10v10" stroke="#cbd5e1" stroke-width="3"/>
<text x="700" y="526" fill="#cbd5e1" font-size="12" font-family="Arial,sans-serif">SOPORTE R-01 · PATÍN</text>
<path d="M888 252v96m-7-96h14m-14 96h14" fill="none" stroke="#cbd5e1" stroke-width="1.5"/>
<path d="m888 252-5 12h10zm0 96-5-12h10z" fill="#cbd5e1"/><text x="904" y="306" fill="#cbd5e1" font-size="11" font-family="Arial,sans-serif" transform="rotate(90 904 306)">OD 114.3 mm</text>
<text x="42" y="552" fill="#64748b" font-size="10" font-family="Arial,sans-serif">CML EN SUPERFICIE EXTERIOR · FLECHA DE FLUJO → · COTAS REFERENCIALES</text>
</svg>""",
    "vessel": """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600" viewBox="0 0 1000 600" preserveAspectRatio="none">
<defs>
  <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#1e293b" stroke-width="1"/></pattern>
  <pattern id="major" width="100" height="100" patternUnits="userSpaceOnUse"><path d="M100 0H0V100" fill="none" stroke="#26364a" stroke-width="1.2"/></pattern>
  <linearGradient id="shell" x2="0" y2="1"><stop stop-color="#334155" stop-opacity=".7"/><stop offset=".5" stop-color="#172235" stop-opacity=".9"/><stop offset="1" stop-color="#334155" stop-opacity=".65"/></linearGradient>
  <marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0 0 9 4.5 0 9z" fill="#cbd5e1"/></marker>
</defs>
<rect width="1000" height="600" fill="#0b1120"/><rect width="1000" height="600" fill="url(#grid)"/><rect width="1000" height="600" fill="url(#major)"/>
<rect x="18" y="18" width="964" height="564" rx="5" fill="none" stroke="#334155"/>
<text x="42" y="49" fill="#e2e8f0" font-size="17" font-family="Arial,sans-serif" font-weight="700" letter-spacing="2">PLANO DE ELEVACIÓN · RECIPIENTE A PRESIÓN</text>
<text x="42" y="73" fill="#94a3b8" font-size="12" font-family="Arial,sans-serif">ASME VIII DIV. 1 · ENVOLVENTE CILÍNDRICA · CABEZALES ELIPSOIDALES 2:1</text>
<text x="823" y="48" fill="#38bdf8" font-size="13" font-family="Arial,sans-serif">VES-210</text><text x="823" y="69" fill="#94a3b8" font-size="11" font-family="Arial,sans-serif">SA-516 Gr. 70</text>
<!-- principal shell, formed heads and internal level -->
<path d="M252 222H748V408H252C203 408 170 368 170 315s33-93 82-93z" fill="url(#shell)" stroke="#38bdf8" stroke-width="3"/>
<path d="M748 222c49 0 82 40 82 93s-33 93-82 93" fill="url(#shell)" stroke="#38bdf8" stroke-width="3"/>
<path d="M187 315H813" fill="none" stroke="#38bdf8" stroke-width="1.4" stroke-dasharray="12 7 2 7"/>
<path d="M190 352H810" fill="none" stroke="#14b8a6" stroke-opacity=".4" stroke-width="52"/>
<path d="M193 326H807" fill="none" stroke="#14b8a6" stroke-width="1.5" stroke-dasharray="9 5"/>
<text x="350" y="372" fill="#5eead4" fill-opacity=".8" font-size="11" font-family="Arial,sans-serif">NIVEL DE LÍQUIDO · INDICATIVO</text>
<!-- weld seams and datum -->
<path d="M252 230V400m6-170v170m490-170v170M170 315H830" fill="none" stroke="#fbbf24" stroke-width="1.7" stroke-dasharray="7 4"/>
<path d="M261 253H741m-480 124H741" fill="none" stroke="#cbd5e1" stroke-opacity=".6" stroke-width="1"/>
<text x="344" y="243" fill="#fbbf24" font-size="10" font-family="Arial,sans-serif">JUNTA LONGITUDINAL · LÍNEA DE CENTRO</text>
<text x="274" y="424" fill="#fbbf24" font-size="10" font-family="Arial,sans-serif">SOLDADURAS CIRCUNFERENCIALES</text>
<!-- nozzles, RF flanges and manway -->
<path d="M330 222v-62h35v62m-45-62h55m-50-8h45m-38-8h30" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
<path d="M331 151h34m-31-8h28" stroke="#cbd5e1" stroke-width="3"/>
<text x="309" y="128" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">N1 · ENTRADA</text>
<path d="M655 222v-42h34v42m-43-42h52m-48-8h44" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
<path d="M655 174h34m-31-8h28" stroke="#cbd5e1" stroke-width="3"/>
<text x="640" y="151" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">N2 · VENTEO</text>
<circle cx="500" cy="222" r="41" fill="#172235" stroke="#38bdf8" stroke-width="4"/><circle cx="500" cy="222" r="31" fill="none" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 4"/>
<g fill="#fbbf24"><circle cx="500" cy="184" r="3"/><circle cx="527" cy="195" r="3"/><circle cx="538" cy="222" r="3"/><circle cx="527" cy="249" r="3"/><circle cx="500" cy="260" r="3"/><circle cx="473" cy="249" r="3"/><circle cx="462" cy="222" r="3"/><circle cx="473" cy="195" r="3"/></g>
<text x="469" y="218" fill="#e2e8f0" font-size="10" font-family="Arial,sans-serif">MH-1</text><text x="465" y="233" fill="#94a3b8" font-size="8" font-family="Arial,sans-serif">MANWAY</text>
<!-- outlet and bottom drain with flanges -->
<path d="M170 315h-62m0-15v30m-10-28v26" fill="none" stroke="#38bdf8" stroke-width="6"/>
<path d="M103 298v34m-10-28v22" stroke="#cbd5e1" stroke-width="3"/><text x="40" y="294" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">N3 · SALIDA</text>
<path d="M720 408v54h30v-54m-37 52h44m-39 8h34" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
<path d="M713 461h44m-39 8h34" stroke="#cbd5e1" stroke-width="3"/><text x="755" y="461" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">DRENAJE</text>
<!-- saddle supports and anchor bolts -->
<path d="M320 405q50 45 100 0l16 66H304zM580 405q50 45 100 0l16 66H564z" fill="#1e293b" stroke="#cbd5e1" stroke-width="2.5"/>
<path d="M301 472h138m123 0h138" stroke="#38bdf8" stroke-width="4"/>
<path d="M316 472v19m108-19v19m124-19v19m108-19v19" stroke="#cbd5e1" stroke-width="3"/>
<path d="M294 494h152m108 0h152" stroke="#64748b" stroke-width="2"/>
<text x="343" y="518" fill="#94a3b8" font-size="10" font-family="Arial,sans-serif">SILLETAS · PERNOS DE ANCLAJE</text>
<!-- sight glass and pressure gauge -->
<path d="M850 283v70m-11 0h22m-22-70h22m-11-25v25" fill="none" stroke="#38bdf8" stroke-width="3"/>
<path d="M844 300h12v40h-12z" fill="#14b8a6" fill-opacity=".35" stroke="#cbd5e1" stroke-width="1.5"/>
<circle cx="850" cy="240" r="20" fill="#111827" stroke="#38bdf8" stroke-width="2"/><path d="m850 240 9-9" stroke="#fbbf24" stroke-width="2"/>
<text x="877" y="244" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">PI-01</text>
<text x="867" y="322" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif" transform="rotate(90 867 322)">VISOR DE NIVEL</text>
<!-- principal dimensions -->
<path d="M170 127H830m-660-8v16m660-16v16" fill="none" stroke="#cbd5e1" stroke-width="1.3" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
<text x="441" y="116" fill="#cbd5e1" font-size="11" font-family="Arial,sans-serif">LONGITUD T/T</text>
<path d="M897 222v186m-8-186h16m-16 186h16" fill="none" stroke="#cbd5e1" stroke-width="1.3" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
<text x="920" y="312" fill="#cbd5e1" font-size="11" font-family="Arial,sans-serif" transform="rotate(90 920 312)">DIÁMETRO INTERIOR</text>
<text x="42" y="552" fill="#64748b" font-size="10" font-family="Arial,sans-serif">ELEVACIÓN DE ENVOLVENTE · CABEZALES FORMADOS · BOQUILLAS REFERENCIALES</text>
</svg>""",
    "tank": """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600" viewBox="0 0 1000 600" preserveAspectRatio="none">
<defs>
  <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#1e293b" stroke-width="1"/></pattern>
  <pattern id="major" width="100" height="100" patternUnits="userSpaceOnUse"><path d="M100 0H0V100" fill="none" stroke="#26364a" stroke-width="1.2"/></pattern>
  <linearGradient id="tankShell" x2="1" y2="0"><stop stop-color="#334155" stop-opacity=".55"/><stop offset=".5" stop-color="#172235" stop-opacity=".8"/><stop offset="1" stop-color="#334155" stop-opacity=".55"/></linearGradient>
  <marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0 0 9 4.5 0 9z" fill="#cbd5e1"/></marker>
</defs>
<rect width="1000" height="600" fill="#0b1120"/><rect width="1000" height="600" fill="url(#grid)"/><rect width="1000" height="600" fill="url(#major)"/>
<rect x="18" y="18" width="964" height="564" rx="5" fill="none" stroke="#334155"/>
<text x="42" y="49" fill="#e2e8f0" font-size="17" font-family="Arial,sans-serif" font-weight="700" letter-spacing="2">ELEVACIÓN DE MANTO · TANQUE ATMOSFÉRICO</text>
<text x="42" y="73" fill="#94a3b8" font-size="12" font-family="Arial,sans-serif">API 650 / API 653 · VIROLAS DEL MANTO · MÉTODO DE 1 PIE</text>
<text x="824" y="48" fill="#38bdf8" font-size="13" font-family="Arial,sans-serif">TK-305</text><text x="824" y="69" fill="#94a3b8" font-size="11" font-family="Arial,sans-serif">D = 24 m · G = 0.85</text>
<!-- ringwall and four shell courses -->
<path d="M270 178H730V260h10v83h10v83h10v84H240v-84h10v-83h10v-83h10z" fill="url(#tankShell)" stroke="#38bdf8" stroke-width="3"/>
<path d="M260 426H760M250 343H750M260 260H740" fill="none" stroke="#cbd5e1" stroke-width="2.2"/>
<path d="M260 426H760M250 343H750M260 260H740" fill="none" stroke="#38bdf8" stroke-width="1" stroke-dasharray="9 5"/>
<path d="M338 178V510m326-332v332" stroke="#fbbf24" stroke-width="1.6" stroke-dasharray="8 5"/>
<text x="260" y="493" fill="#e2e8f0" font-size="12" font-family="Arial,sans-serif" font-weight="700">VIROLA 1 · INFERIOR / MAYOR ESPESOR</text>
<text x="260" y="410" fill="#cbd5e1" font-size="11" font-family="Arial,sans-serif">VIROLA 2</text>
<text x="260" y="327" fill="#cbd5e1" font-size="11" font-family="Arial,sans-serif">VIROLA 3</text>
<text x="260" y="244" fill="#cbd5e1" font-size="11" font-family="Arial,sans-serif">VIROLA 4 · SUPERIOR</text>
<!-- liquid and level datum -->
<path d="M254 310H746V507H254z" fill="#0e7490" fill-opacity=".18"/>
<path d="M254 310H746" stroke="#2dd4bf" stroke-width="2" stroke-dasharray="10 5"/>
<text x="473" y="300" fill="#5eead4" font-size="11" font-family="Arial,sans-serif">NIVEL DE OPERACIÓN</text>
<!-- fixed cone roof, guardrail and center vent -->
<path d="m230 178 270-82 270 82z" fill="#172235" fill-opacity=".92" stroke="#38bdf8" stroke-width="3"/>
<path d="m250 166 250-72 250 72M245 157l255-74 255 74" fill="none" stroke="#cbd5e1" stroke-width="1.6"/>
<path d="M229 178h542m-528-9v-24m514 24v-24m-514 0h514" fill="none" stroke="#38bdf8" stroke-width="2"/>
<path d="M485 96V73h30v23m-24-23h18" fill="#172235" stroke="#cbd5e1" stroke-width="2"/>
<text x="445" y="63" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">VENTEO / TECHO CÓNICO FIJO</text>
<text x="763" y="177" fill="#94a3b8" font-size="10" font-family="Arial,sans-serif">BARANDA PERIMETRAL</text>
<!-- roof access stair and cage -->
<path d="M814 490 847 184m-27 279 35 4m-31-42 35 4m-26-47 34 4m-30-47 34 4m-29-47 35 4m-31-48 35 4m-30-46 36 4m-31-46 36 4m-31-45 35 4" fill="none" stroke="#cbd5e1" stroke-width="2"/>
<path d="M814 490 847 184m-19 289 38-353" fill="none" stroke="#38bdf8" stroke-width="1.5"/>
<text x="861" y="350" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif" transform="rotate(-84 861 350)">ESCALERA DE ACCESO</text>
<!-- inlet and outlet with flanges -->
<path d="M670 178v-56h26v56m-34-56h42m-38-7h34" fill="#172235" stroke="#38bdf8" stroke-width="3"/>
<path d="M662 122h42m-37-7h32" stroke="#cbd5e1" stroke-width="3"/>
<text x="697" y="139" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">N1 · ENTRADA</text>
<path d="M250 458h-55v25h55m-55-33v42m-8-37v32" fill="#172235" stroke="#38bdf8" stroke-width="3"/>
<path d="M195 450v42m-8-37v32" stroke="#cbd5e1" stroke-width="3"/>
<text x="91" y="451" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">SALIDA / BRIDA</text>
<!-- cleanout door and base -->
<path d="M315 510v-44q30-26 60 0v44m-60-41h60" fill="#111827" stroke="#cbd5e1" stroke-width="3"/>
<g fill="#fbbf24"><circle cx="321" cy="476" r="2.5"/><circle cx="369" cy="476" r="2.5"/><circle cx="321" cy="501" r="2.5"/><circle cx="369" cy="501" r="2.5"/></g>
<text x="383" y="478" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif">BOCA DE LIMPIEZA</text>
<path d="M230 510h540v20H230z" fill="#334155" stroke="#cbd5e1" stroke-width="2"/>
<path d="M210 530h580m-540 7v12m500-12v12" stroke="#94a3b8" stroke-width="3"/>
<text x="409" y="560" fill="#cbd5e1" font-size="11" font-family="Arial,sans-serif">ANILLO DE HORMIGÓN · BASE NIVELADA</text>
<!-- course reference dimensions -->
<path d="M214 178v332m-8-332h16m-16 332h16" fill="none" stroke="#cbd5e1" stroke-width="1.3" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
<text x="194" y="356" fill="#cbd5e1" font-size="10" font-family="Arial,sans-serif" transform="rotate(-90 194 356)">ALTURA MANTO</text>
<path d="M250 540H750m-500-7v14m500-14v14" stroke="#cbd5e1" stroke-width="1.2" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
<text x="470" y="535" fill="#94a3b8" font-size="9" font-family="Arial,sans-serif">D = 24 m</text>
<text x="42" y="574" fill="#64748b" font-size="10" font-family="Arial,sans-serif">INSPECCIÓN UT EXTERNA · JUNTAS DE VIROLAS · REFERENCIA DE CAMPAÑA</text>
</svg>""",
}


def q(value):
    return html.escape(str(value), quote=True)


def number(value, digits=2):
    if value is None:
        return "—"
    return f"{float(value):,.{digits}f}"


def show_message(message, error=False):
    element = document.querySelector("#app-message")
    element.textContent = str(message)
    element.className = "message-bar error" if error else "message-bar info"
    element.hidden = False


def hide_message():
    document.querySelector("#app-message").hidden = True


def save_data():
    localStorage.setItem(STORAGE_KEY, json.dumps(DATA, ensure_ascii=False))


def equipment_by_id(equipment_id):
    return next((item for item in DATA["equipment"] if item["id"] == equipment_id), None)


def validate_project(project):
    if not isinstance(project, dict) or not isinstance(project.get("equipment"), list):
        raise ValueError("El JSON debe ser un objeto con una lista 'equipment'.")
    equipment_ids = set()
    for equipment in project["equipment"]:
        if not isinstance(equipment, dict):
            raise ValueError("Cada equipo debe ser un objeto JSON.")
        equipment_id = equipment.get("id")
        if not isinstance(equipment_id, str) or not equipment_id.strip() or equipment_id in equipment_ids:
            raise ValueError("Cada equipo requiere un id de texto único.")
        equipment_ids.add(equipment_id)
        if equipment.get("family") not in FAMILY_NAMES:
            raise ValueError(f"Familia inválida en el equipo {equipment_id}.")
        if not isinstance(equipment.get("name"), str) or not isinstance(equipment.get("location"), str):
            raise ValueError(f"Faltan identificación o ubicación en {equipment_id}.")
        family_calculation(equipment)
        points = equipment.get("cmls", [])
        if not isinstance(points, list):
            raise ValueError(f"'cmls' debe ser una lista en {equipment_id}.")
        point_ids = set()
        for point in points:
            if not isinstance(point, dict) or not isinstance(point.get("id"), str):
                raise ValueError(f"Hay un punto CML/TML inválido en {equipment_id}.")
            if point["id"] in point_ids:
                raise ValueError(f"ID de punto duplicado {point['id']} en {equipment_id}.")
            point_ids.add(point["id"])
            for coordinate in ("x", "y"):
                value = float(point.get(coordinate, 50))
                if not isfinite(value) or not 0 <= value <= 100:
                    raise ValueError(f"La coordenada {coordinate} de {point['id']} debe estar entre 0 y 100.")
            measurements = point.get("measurements", [])
            if not isinstance(measurements, list):
                raise ValueError(f"'measurements' debe ser una lista en {point['id']}.")
            for item in measurements:
                if not isinstance(item, dict):
                    raise ValueError(f"Medición inválida en {point['id']}.")
                date.fromisoformat(str(item["date"]))
                thickness = float(item["thickness_mm"])
                if not isfinite(thickness) or thickness <= 0:
                    raise ValueError(f"Espesor inválido en {point['id']}.")


def point_by_id(equipment, point_id):
    return next((point for point in equipment.get("cmls", []) if point["id"] == point_id), None)


def family_calculation(equipment, measured=None, rate=0.0):
    common = {
        "nominal_thickness_mm": equipment["nominal_thickness_mm"],
        "measured_thickness_mm": measured,
        "corrosion_rate_mm_per_year": max(0.0, rate),
    }
    family = equipment["family"]
    if family == "pipe":
        return calculate_pipe(
            pressure_mpa=equipment["design_pressure_mpa"],
            outside_diameter_mm=equipment["outside_diameter_mm"],
            allowable_stress_mpa=equipment["allowable_stress_mpa"],
            weld_efficiency=equipment["weld_efficiency"],
            weld_strength_reduction=equipment.get("weld_strength_reduction", 1.0),
            coefficient_y=equipment.get("coefficient_y", 0.4),
            mill_tolerance_fraction=equipment.get("mill_tolerance_fraction", 0.125),
            corrosion_allowance_mm=equipment.get("corrosion_allowance_mm", 0.0),
            **common,
        )
    if family == "vessel":
        return calculate_vessel(
            pressure_mpa=equipment["design_pressure_mpa"],
            inside_radius_mm=equipment["inside_radius_mm"],
            allowable_stress_mpa=equipment["allowable_stress_mpa"],
            weld_efficiency=equipment["weld_efficiency"],
            mill_tolerance_fraction=equipment.get("mill_tolerance_fraction", 0.0),
            corrosion_allowance_mm=equipment.get("corrosion_allowance_mm", 0.0),
            **common,
        )
    if family == "tank":
        result = calculate_tank(
            diameter_m=equipment["tank_diameter_m"],
            liquid_height_m=equipment["liquid_height_m"],
            specific_gravity=equipment["specific_gravity"],
            allowable_stress_mpa=equipment["allowable_stress_mpa"],
            measured_thickness_mm=measured,
            nominal_thickness_mm=equipment["nominal_thickness_mm"],
            corrosion_rate_mm_per_year=max(0.0, rate),
        )
        return result
    raise ValueError(f"Familia no reconocida: {family}")


def point_analysis(equipment, point):
    base = family_calculation(equipment)
    corrosion = calculate_corrosion(point.get("measurements", []), base["t_min_mm"])
    if not point.get("measurements"):
        return base, corrosion, base
    rate = corrosion.get("cr_governing_mm_per_year") or 0.0
    result = family_calculation(equipment, point["measurements"][-1]["thickness_mm"], rate)
    if corrosion["status"] == "below_minimum":
        result["condition"] = "critical"
        result["condition_text"] = corrosion["message"]
    elif corrosion["status"] in ("insufficient", "date_error"):
        result["condition"] = "insufficient" if corrosion["status"] == "insufficient" else "error"
        result["condition_text"] = corrosion["message"]
    elif corrosion["status"] == "no_corrosion":
        result["condition"] = "insufficient"
        result["condition_text"] = corrosion["message"]
    return base, corrosion, result


def equipment_condition(equipment):
    if not equipment.get("cmls"):
        return "insufficient"
    conditions = []
    for point in equipment["cmls"]:
        try:
            _, corrosion, result = point_analysis(equipment, point)
            conditions.append(result["condition"])
            if result["condition"] in ("critical", "insufficient", "error"):
                continue
            interval = calculate_inspection_interval(
                equipment["family"],
                corrosion.get("remaining_life_years"),
                pipe_class_max_years=equipment.get("inspection_class_max_years"),
                corrosion_rate_known=corrosion.get("cr_governing_mm_per_year") is not None,
            )
            if interval["interval_years"] is not None:
                last_date = date.fromisoformat(point["measurements"][-1]["date"])
                due_date = last_date + timedelta(days=interval["interval_years"] * 365.25)
                if date.today() > due_date:
                    conditions.append("overdue")
        except (ValueError, KeyError, TypeError):
            conditions.append("error")
    for status in ("critical", "overdue", "error", "alert", "insufficient"):
        if status in conditions:
            return status
    return "normal"


def status_pill(status):
    label = STATUS_NAMES.get(status, status)
    style = "critical" if status in ("below_minimum", "overdue") else status
    return f'<span class="pill status-{q(style)}">{q(label)}</span>'


def fill_select(select_id, options, selected=None, include_all=False):
    element = document.querySelector(select_id)
    current = selected if selected is not None else element.value
    choices = []
    if include_all:
        choices.append('<option value="">Todos los equipos</option>')
    for value, label in options:
        choices.append(f'<option value="{q(value)}">{q(label)}</option>')
    element.innerHTML = "".join(choices)
    if any(value == current for value, _ in options):
        element.value = current
    elif options:
        element.value = options[0][0]
    return element.value


def all_point_options():
    return [
        (f"{equipment['id']}::{point['id']}", f"{equipment['name']} · {point['id']}")
        for equipment in DATA["equipment"] for point in equipment.get("cmls", [])
    ]


def render_dashboard():
    family_filter = document.querySelector("#filter-family").value
    location_filter = document.querySelector("#filter-location").value.strip().casefold()
    condition_filter = document.querySelector("#filter-condition").value
    rows = []
    for equipment in DATA["equipment"]:
        status = equipment_condition(equipment)
        if family_filter and equipment["family"] != family_filter:
            continue
        if location_filter and location_filter not in equipment["location"].casefold():
            continue
        if condition_filter and status != condition_filter:
            continue
        try:
            minimum = family_calculation(equipment)["t_min_mm"]
            minimum_text = f"{number(minimum, 3)} mm"
        except (ValueError, KeyError, TypeError):
            minimum_text = "Error de datos"
        rows.append(
            "<tr>"
            f'<td><button class="equipment-link" data-edit="{q(equipment["id"])}">{q(equipment["name"])}</button></td>'
            f'<td>{q(FAMILY_NAMES.get(equipment["family"], equipment["family"]))}</td>'
            f'<td>{q(equipment["location"])}</td><td>{minimum_text}</td>'
            f'<td>{status_pill(status)}</td><td><button class="text-action" data-measure="{q(equipment["id"])}">Ver</button></td>'
            "</tr>"
        )
    total = len(DATA["equipment"])
    counts = {key: sum(equipment_condition(item) == key for item in DATA["equipment"]) for key in ("normal", "alert", "critical", "overdue", "insufficient")}
    document.querySelector("#summary-cards").innerHTML = "".join(
        f'<article class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-foot">{foot}</div></article>'
        for label, value, foot in (
            ("Equipos registrados", total, "Activos en el proyecto"),
            ("Condición normal", counts["normal"], "Sin umbral excedido"),
            ("En alerta", counts["alert"], "Requieren planificación"),
            ("Críticos / vencidos / sin datos", counts["critical"] + counts["overdue"] + counts["insufficient"], "Revisión prioritaria"),
        )
    )
    document.querySelector("#equipment-table").innerHTML = "".join(rows) if rows else '<tr><td colspan="6"><div class="empty-state">No hay equipos que coincidan con los filtros.</div></td></tr>'
    document.querySelector("#asset-count").textContent = f"{len(rows)} de {total} equipos"


def populate_equipment_form(equipment):
    document.querySelector("#equipment-name").value = equipment.get("name", "")
    document.querySelector("#equipment-location").value = equipment.get("location", "")
    document.querySelector("#equipment-material").value = equipment.get("material_specification", "")
    document.querySelector("#equipment-family").value = equipment.get("family", "pipe")
    for key in FIELD_KEYS:
        field = document.querySelector(f'[data-field="{key}"]')
        field.value = equipment.get(key, "")
    try:
        calculation = family_calculation(equipment)
        input_rows = "<br>".join(
            f"{q(key)} = {number(value, 4)}"
            for key, value in calculation["inputs"].items()
        )
        input_rows += (
            f"<br>t nominal = {number(calculation['t_nominal_mm'], 3)} mm"
            f"<br>Tolerancia fabricación = {number(calculation['mill_tolerance_fraction'] * 100, 2)} %"
            f"<br>CA = {number(calculation['corrosion_allowance_mm'], 3)} mm"
            f"<br>Material = {q(equipment.get('material_specification', 'No especificado'))}"
        )
        document.querySelector("#equipment-design-summary").innerHTML = (
            '<div class="design-trace">'
            f'<section class="trace-card trace-inputs"><h3>Datos de entrada · unidades</h3><p>{input_rows}</p></section>'
            f'<section class="trace-card trace-equation"><h3>Ecuación aplicada</h3><p><code>{q(calculation["formula"])}</code></p></section>'
            f'<section class="trace-card trace-reference"><h3>Referencia normativa</h3><p>{q(calculation["reference"])}</p></section>'
            '<section class="trace-card trace-result"><h3>Resultado de diseño</h3>'
            f'<p>Espesor requerido / mínimo</p><strong class="design-result-value">{number(calculation["t_min_mm"], 3)} mm</strong>'
            f'<p>Nominal requerido con CA y tolerancia: <strong>{number(calculation["nominal_required_mm"], 3)} mm</strong></p>'
            f'<p>t alerta inicial: {number(calculation["t_alert_mm"], 3)} mm</p></section></div>'
        )
    except (ValueError, KeyError, TypeError) as exc:
        document.querySelector("#equipment-design-summary").textContent = f"Datos de diseño incompletos o inválidos: {exc}"


def render_schematic():
    equipment = equipment_by_id(document.querySelector("#schematic-equipment").value)
    if equipment is None:
        document.querySelector("#schematic-canvas").innerHTML = '<div class="empty-state">Seleccione un equipo con esquema.</div>'
        document.querySelector("#cml-list").innerHTML = ""
        return
    schematic_key = equipment.get("schematic_id", equipment["family"])
    svg = SCHEMATICS.get(schematic_key, SCHEMATICS.get(equipment["family"], SCHEMATICS["pipe"]))
    generated_uri = "data:image/svg+xml;charset=utf-8," + quote(svg)
    image_uri = equipment.get("schematic_image_data") or generated_uri
    image_alt = (
        f"Plano adjunto de {q(equipment['name'])}"
        if equipment.get("schematic_image_data")
        else f"Plano técnico ilustrativo de {q(equipment['name'])}"
    )
    markers = []
    listings = []
    for index, point in enumerate(equipment.get("cmls", []), start=1):
        try:
            if not point.get("measurements"):
                status, thickness = "insufficient", "—"
                status_info, cr_text = status_pill(status), "—"
                last_date = "Sin medición"
            else:
                _, corrosion, result = point_analysis(equipment, point)
                status = result["condition"]
                thickness = point["measurements"][-1]["thickness_mm"]
                status_info = status_pill(status)
                cr_text = number(corrosion.get("cr_governing_mm_per_year"), 3)
                last_date = point["measurements"][-1]["date"]
        except (ValueError, KeyError, TypeError) as exc:
            status, thickness, status_info, cr_text = "error", "—", status_pill("error"), q(exc)
            last_date = "Medición no disponible"
        x = min(100.0, max(0.0, float(point.get("x", 50))))
        y = min(100.0, max(0.0, float(point.get("y", 50))))
        label_side = "marker-label-left" if x >= 58 else "marker-label-right"
        if equipment["family"] == "pipe":
            label_side = "marker-label-left" if index < 3 else "marker-label-below marker-label-left"
        markers.append(
            f'<button class="schematic-marker marker-{q(status)} {label_side}" '
            f'title="{q(point["id"])} · {q(thickness)} mm · {q(last_date)}" '
            f'aria-label="{q(point["id"])}: {STATUS_NAMES.get(status, status)}, espesor {q(thickness)} mm" '
            f'style="left:{x}%;top:{y}%;" data-point="{q(equipment["id"])}::{q(point["id"])}">'
            '<span class="marker-target" aria-hidden="true"><svg viewBox="0 0 32 32">'
            '<circle cx="16" cy="16" r="11"/><circle cx="16" cy="16" r="4"/>'
            '<path d="M16 0v7m0 18v7M0 16h7m18 0h7"/></svg></span>'
            '<span class="marker-leader" aria-hidden="true"></span>'
            f'<span class="marker-label">{q(point["id"])}</span></button>'
        )
        listings.append(
            f'<div class="cml-item">'
            f'<button type="button" class="cml-point-info" data-point="{q(equipment["id"])}::{q(point["id"])}">'
            f'<span class="cml-point-copy"><strong>{q(point["id"])} · {q(point.get("description", ""))}</strong>'
            f'<small>{q(thickness)} mm · CR gob. {cr_text} mm/año</small></span></button>'
            '<div class="cml-actions">'
            f'{status_info}'
            f'<button type="button" class="compact-action" data-edit-cml="{q(equipment["id"])}::{q(point["id"])}">Editar</button>'
            f'<button type="button" class="compact-action compact-action-delete" data-delete-cml="{q(equipment["id"])}::{q(point["id"])}">Eliminar</button>'
            '</div></div>'
        )
    title_suffix = " · Imagen propia" if equipment.get("schematic_image_data") else ""
    document.querySelector("#schematic-title").textContent = f"Esquema · {equipment['name']}{title_suffix}"
    document.querySelector("#schematic-canvas").innerHTML = (
        f'<img class="schematic-image" alt="{image_alt}" src="{q(image_uri)}">'
        f'{"".join(markers)}'
    )
    document.querySelector("#cml-list").innerHTML = "".join(listings) or '<div class="empty-state">Sin puntos CML/TML registrados.</div>'


def on_schematic_image_upload(event):
    files = event.currentTarget.files
    if files.length == 0:
        return
    selected_file = files.item(0)
    event.currentTarget.value = ""
    filename = str(selected_file.name).lower()
    content_type = str(selected_file.type).lower()
    allowed_type = content_type in ("image/png", "image/jpeg")
    allowed_extension = filename.endswith((".png", ".jpg", ".jpeg"))
    if not allowed_type or not allowed_extension:
        show_message("Seleccione una imagen PNG o JPG válida.", error=True)
        return
    if selected_file.size > 2 * 1024 * 1024:
        show_message("La imagen debe pesar 2 MB o menos para guardarse localmente.", error=True)
        return
    equipment = equipment_by_id(document.querySelector("#schematic-equipment").value)
    if equipment is None:
        show_message("Seleccione un equipo antes de adjuntar el plano.", error=True)
        return
    reader = FileReader.new()

    def on_load(_event):
        image_data = str(reader.result)
        if not image_data.startswith(("data:image/png;base64,", "data:image/jpeg;base64,")):
            show_message("El archivo seleccionado no se pudo leer como PNG o JPG.", error=True)
            return
        equipment["schematic_image_data"] = image_data
        save_data()
        render_schematic()
        show_message(f"Plano adjunto guardado para {equipment['name']}.")

    proxy = create_proxy(on_load)
    EVENT_PROXIES.append(proxy)
    reader.addEventListener("load", proxy)
    error_proxy = create_proxy(
        lambda _event: show_message("No se pudo leer la imagen seleccionada.", error=True)
    )
    EVENT_PROXIES.append(error_proxy)
    reader.addEventListener("error", error_proxy)
    reader.readAsDataURL(selected_file)


def show_generated_schematic(_event):
    equipment = equipment_by_id(document.querySelector("#schematic-equipment").value)
    if equipment is None:
        show_message("Seleccione un equipo para mostrar su plano técnico.", error=True)
        return
    equipment.pop("schematic_image_data", None)
    save_data()
    render_schematic()
    show_message(f"Se muestra el plano técnico generado para {equipment['name']}.")


def render_chart(equipment, point, minimum, corrosion):
    measurements = point.get("measurements", [])
    if len(measurements) < 1:
        document.querySelector("#thickness-chart").innerHTML = '<div class="empty-state">Sin mediciones para graficar.</div>'
        return
    dates = [datetime.fromisoformat(item["date"]) for item in measurements]
    thickness = np.asarray([item["thickness_mm"] for item in measurements], dtype=float)
    fig, axis = plt.subplots(figsize=(7.1, 3.2), facecolor="#111827")
    axis.set_facecolor("#111827")
    axis.plot(dates, thickness, marker="o", markersize=7, markeredgecolor="#111827",
              markeredgewidth=1.3, color="#2dd4bf", linewidth=2.5, label="Espesor medido")
    axis.axhline(minimum, color="#fb7185", linestyle="--", linewidth=1.8,
                 label=f"Mínimo {minimum:.2f} mm")
    rate = corrosion.get("cr_governing_mm_per_year")
    if rate and rate > 0 and len(thickness) >= 2:
        years = np.linspace(0, 3, 20)
        end = [dates[-1] + timedelta(days=float(year * 365.25)) for year in years]
        forecast = thickness[-1] - rate * years
        axis.plot(end, forecast, color="#fbbf24", linestyle=":", linewidth=2.2,
                  label="Proyección lineal")
    axis.set_ylabel("Espesor (mm)")
    axis.set_xlabel("Fecha de campaña")
    axis.grid(alpha=0.75)
    for spine in axis.spines.values():
        spine.set_color("#334155")
    axis.legend(frameon=True, facecolor="#1e293b", edgecolor="#334155",
                labelcolor="#e2e8f0", framealpha=0.96, fontsize=10, loc="best")
    fig.autofmt_xdate()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=140, bbox_inches="tight",
                facecolor="#111827", edgecolor="#111827")
    plt.close(fig)
    image = base64.b64encode(buffer.getvalue()).decode("ascii")
    document.querySelector("#thickness-chart").innerHTML = f'<img alt="Gráfico de espesor para {q(point["id"])}" src="data:image/png;base64,{image}">'


def detail_block(title, formula, reference, inputs, outputs):
    input_text = "<br>".join(f"{q(key)} = {q(value)}" for key, value in inputs.items())
    output_text = "<br>".join(f"{q(key)} = {q(value)}" for key, value in outputs.items())
    return (
        f'<article class="trace-card trace-inputs"><h3>{q(title)} · Datos de entrada</h3>'
        f'<p>{input_text}</p></article>'
        f'<article class="trace-card trace-equation"><h3>Ecuación aplicada</h3>'
        f'<p><code>{q(formula)}</code></p></article>'
        f'<article class="trace-card trace-reference"><h3>Referencia normativa</h3>'
        f'<p>{q(reference)}</p></article>'
        f'<article class="trace-card trace-result"><h3>Resultado</h3>'
        f'<p>{output_text}</p></article>'
    )


def render_measurement():
    value = document.querySelector("#measurement-point").value
    if not value:
        document.querySelector("#measurement-result").innerHTML = '<div class="empty-state">No hay puntos CML/TML cargados.</div>'
        document.querySelector("#thickness-chart").innerHTML = ""
        document.querySelector("#measurement-history").innerHTML = ""
        document.querySelector("#calculation-details").innerHTML = ""
        return
    equipment_id, point_id = value.split("::", 1)
    equipment = equipment_by_id(equipment_id)
    point = point_by_id(equipment, point_id)
    if equipment is None or point is None or not point.get("measurements"):
        document.querySelector("#measurement-result").innerHTML = '<div class="empty-state">Punto sin mediciones; registre la primera campaña abajo.</div>'
        document.querySelector("#thickness-chart").innerHTML = '<div class="empty-state">Sin mediciones para graficar.</div>'
        document.querySelector("#measurement-history").innerHTML = '<div class="empty-state">Sin historial UT.</div>'
        document.querySelector("#calculation-details").innerHTML = ""
        if point is not None:
            show_message(f"El punto {point_id} aún no tiene mediciones. Registre una campaña.", error=False)
        return
    try:
        base, corrosion, calculated = point_analysis(equipment, point)
        interval = calculate_inspection_interval(
            equipment["family"],
            corrosion.get("remaining_life_years"),
            pipe_class_max_years=equipment.get("inspection_class_max_years"),
            corrosion_rate_known=corrosion.get("cr_governing_mm_per_year") is not None,
        )
    except (ValueError, KeyError, TypeError) as exc:
        show_message(f"No fue posible calcular el punto {point_id}: {exc}", error=True)
        return
    rate = corrosion.get("cr_governing_mm_per_year")
    corrosion_status = "critical" if corrosion["status"] == "below_minimum" else "alert" if rate and rate > 0 else "insufficient" if rate is None else "normal"
    cards = [
        ("Velocidad de corrosión", f"{number(rate, 3)} mm/año",
         f"CR corto plazo {number(corrosion.get('cr_st_mm_per_year'), 3)} · CR largo plazo {number(corrosion.get('cr_lt_mm_per_year'), 3)}",
         corrosion_status, "CR gobernante"),
        ("Vida remanente", f"{number(corrosion.get('remaining_life_years'), 2)} años",
         "Calculada desde el espesor actual y mínimo",
         "critical" if corrosion["status"] == "below_minimum" else "normal" if corrosion.get("remaining_life_years") is not None else "insufficient",
         "RL"),
    ]
    due_text = "No calculable"
    due_status = "insufficient"
    if interval["interval_years"] is not None:
        last_date = date.fromisoformat(point["measurements"][-1]["date"])
        due_date = last_date + timedelta(days=interval["interval_years"] * 365.25)
        overdue = date.today() > due_date
        due_text = f"VENCIDA · {due_date.isoformat()}" if overdue else due_date.isoformat()
        due_status = "critical" if overdue else "normal"
    cards.append((
        "Próxima inspección",
        due_text,
        f"Intervalo {number(interval['interval_years'], 2)} años desde última campaña · {interval['basis']}",
        due_status,
        "Vencida" if due_status == "critical" else "Fecha objetivo",
    ))
    cards.append((
        "Condición del punto",
        STATUS_NAMES.get(calculated["condition"], calculated["condition"]),
        f"Espesor actual {number(point['measurements'][-1]['thickness_mm'], 3)} mm · mínimo {number(base['t_min_mm'], 3)} mm",
        "critical" if calculated["condition"] == "critical" else "alert" if calculated["condition"] == "alert" else "normal" if calculated["condition"] == "normal" else "insufficient",
        "Estado CML/TML",
    ))
    document.querySelector("#measurement-result").innerHTML = "".join(
        f'<article class="metric-card metric-kpi"><div class="metric-label">{q(label)}</div>'
        f'<div class="metric-value">{q(value)}</div><div class="metric-foot">{q(foot)}</div>'
        f'<span class="kpi-badge status-{q(status)}">{q(badge)}</span></article>'
        for label, value, foot, status, badge in cards
    )
    render_chart(equipment, point, base["t_min_mm"], corrosion)
    history_rows = "".join(
        f'<tr><td>{q(item["date"])}</td><td>{number(item["thickness_mm"], 3)} mm</td>'
        f'<td>{"Sí" if item.get("reset_baseline") else "No"}</td>'
        f'<td><button type="button" class="compact-action compact-action-delete" '
        f'data-delete-measurement="{index}">Eliminar</button></td></tr>'
        for index, item in enumerate(point["measurements"])
    )
    document.querySelector("#measurement-history").innerHTML = (
        "<table><thead><tr><th>Fecha</th><th>Espesor</th><th>Reinicio de línea base</th><th>Acción</th></tr></thead>"
        f"<tbody>{history_rows}</tbody></table>"
    )
    current = point["measurements"][-1]["thickness_mm"]
    applied = family_calculation(equipment, current, rate or 0.0)
    details = detail_block(
        "Espesor mínimo y de alerta",
        applied["formula"],
        applied["reference"],
        {**{k: number(v, 4) for k, v in applied["inputs"].items()},
         "t_nominal (mm)": number(applied["t_nominal_mm"], 3),
         "tolerancia fabricación (%)": f"{number(applied['mill_tolerance_fraction'] * 100, 2)} %",
         "CA (mm)": number(applied["corrosion_allowance_mm"], 3),
         "material": equipment.get("material_specification", "No especificado"),
         "CR gobernante (mm/año)": number(rate, 4),
         "horizonte de intervención (años)": applied["intervention_horizon_years"]},
        {"t_req / t_min (mm)": number(applied["t_min_mm"], 3),
         "t nominal requerido (mm)": number(applied["nominal_required_mm"], 3),
         "t medido (mm)": number(current, 3),
         "t alerta (mm)": number(applied["t_alert_mm"], 3),
         "base t_alert": "t_min + CR_gob × horizonte; pérdida prevista antes de la intervención planificada",
         "condición": applied["condition_text"]},
    )
    details += detail_block(
        "Corrosión y vida remanente",
        "CR_ST=(t_anterior−t_actual)/Δt; CR_LT=(t_inicial−t_actual)/Δt; CR_gob=max(CR_ST, CR_LT); RL=(t_actual−t_min)/CR_gob",
        "Criterio conservador solicitado; API 570 / API 510 / API 653 según familia.",
        {"Punto": point["id"], "mediciones": len(point["measurements"]),
         "campañas (fecha · espesor)": " · ".join(
             f"{item['date']}: {number(item['thickness_mm'], 3)} mm"
             for item in point["measurements"]
         ),
         "reinicio de línea base": corrosion.get("baseline_reset", False)},
        {"CR_ST (mm/año)": number(corrosion.get("cr_st_mm_per_year"), 4),
         "CR_LT (mm/año)": number(corrosion.get("cr_lt_mm_per_year"), 4),
         "CR gobernante (mm/año)": number(rate, 4),
         "RL (años)": number(corrosion.get("remaining_life_years"), 3),
         "estado": corrosion["message"]},
    )
    document.querySelector("#calculation-details").innerHTML = f'<div class="detail-grid">{details}</div>'
    hide_message()


def draw_risk_matrix(result):
    matrix = np.array([
        [
            1 if (row + 1) * (column + 1) <= 4 else
            2 if (row + 1) * (column + 1) <= 9 else
            3 if (row + 1) * (column + 1) <= 16 else 4
            for column in range(5)
        ]
        for row in range(5)
    ])
    from matplotlib.colors import ListedColormap

    fig, axis = plt.subplots(figsize=(5.4, 4.0), constrained_layout=True,
                             facecolor="#111827")
    axis.set_facecolor("#111827")
    axis.imshow(
        matrix,
        origin="lower",
        cmap=ListedColormap(["#123c31", "#3a3216", "#4a2d17", "#4a2028"]),
        vmin=1,
        vmax=4,
    )
    axis.set_xticks(range(5), ["1", "2", "3", "4", "5"])
    axis.set_yticks(range(5), ["1", "2", "3", "4", "5"])
    axis.set_xlabel("Consecuencia de área (CA)")
    axis.set_ylabel("Frecuencia de falla (fF)")
    axis.set_title("Matriz de cribado 5 × 5")
    axis.set_xticks(np.arange(-0.5, 5, 1), minor=True)
    axis.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    axis.grid(which="minor", color="#334155", linewidth=1.5)
    axis.tick_params(which="minor", bottom=False, left=False)
    for spine in axis.spines.values():
        spine.set_color("#475569")
    category_names = ("B", "M", "A", "MA")
    for row in range(5):
        for column in range(5):
            axis.text(column, row, category_names[matrix[row, column] - 1],
                      ha="center", va="center", fontsize=10, fontweight="bold",
                      color="#f8fafc")
    x = result["consequence_level"] - 1
    y = result["likelihood_level"] - 1
    axis.scatter([x], [y], marker="*", s=280, edgecolor="#f8fafc",
                 linewidth=1.1, facecolor="#38bdf8", label="Equipo evaluado",
                 zorder=5)
    axis.legend(loc="upper left", bbox_to_anchor=(0, -0.18), frameon=True,
                facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0",
                fontsize=10)
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=140, bbox_inches="tight",
                facecolor="#111827", edgecolor="#111827")
    plt.close(fig)
    image = base64.b64encode(buffer.getvalue()).decode("ascii")
    document.querySelector("#risk-matrix").innerHTML = f'<img alt="Matriz de riesgo con el equipo en nivel de consecuencia {result["consequence_level"]} y frecuencia {result["likelihood_level"]}" src="data:image/png;base64,{image}">'


def rbi_result_card(label, value, badge_status=None):
    if badge_status:
        value_markup = f'<span class="kpi-badge status-{q(badge_status)}">{q(value)}</span>'
    else:
        value_markup = q(value)
    return f'<div class="rbi-value"><small>{q(label)}</small><strong>{value_markup}</strong></div>'


def render_rbi(event=None):
    equipment = equipment_by_id(document.querySelector("#rbi-equipment").value)
    if equipment is None or not equipment.get("cmls"):
        document.querySelector("#rbi-result").textContent = "Seleccione un equipo con mediciones."
        return
    try:
        points = []
        for point in equipment["cmls"]:
            _, corrosion, result = point_analysis(equipment, point)
            if corrosion.get("cr_governing_mm_per_year") is not None:
                points.append((corrosion["cr_governing_mm_per_year"], point, corrosion))
        if not points:
            raise ValueError("No hay una tasa de corrosión positiva calculable para este equipo.")
        rate, point, corrosion = max(points, key=lambda row: row[0])
        age = float(document.querySelector("#rbi-age").value)
        f0 = float(document.querySelector("#rbi-base-frequency").value)
        fms = float(document.querySelector("#rbi-management-factor").value)
        area = float(document.querySelector("#rbi-area").value)
        economic = float(document.querySelector("#rbi-economic").value)
        currency = document.querySelector("#rbi-currency").value
        result = calculate_rbi(
            rate, age, equipment["nominal_thickness_mm"], f0, fms, area, economic
        )
        DATA["rbi"] = {
            "equipment_id": equipment["id"],
            "service_age_years": age,
            "base_failure_frequency_per_year": f0,
            "management_factor": fms,
            "consequence_area_m2": area,
            "economic_consequence": economic,
            "currency": currency,
        }
        save_data()
        draw_risk_matrix(result)
    except (ValueError, KeyError, TypeError) as exc:
        show_message(f"No fue posible calcular RBI: {exc}", error=True)
        return
    priority_status = {
        "Baja": "normal",
        "Moderada": "info",
        "Alta": "alert",
        "Muy alta": "critical",
    }.get(result["inspection_priority"], "insufficient")
    document.querySelector("#rbi-result").innerHTML = "".join(
        rbi_result_card(
            label,
            value,
            priority_status if label == "Prioridad de inspección" else None,
        )
        for label, value in (
            ("Equipo / CML gobernante", f"{equipment['name']} / {point['id']}"),
            ("Ar = CR·edad/t_nom", number(result["area_ratio"], 4)),
            ("Df escalonado (no probabilidad)", number(result["damage_factor"], 2)),
            ("Frecuencia fF (1/año)", f"{result['failure_frequency_per_year']:.4g}"),
            ("Riesgo de área RA (m²/año)", f"{result['area_risk_m2_per_year']:.4g}"),
            (f"Riesgo económico RE ({currency}/año)", f"{result['economic_risk_per_year']:.4g} {currency}/año"),
            ("Nivel matriz (fF, CA)", f"{result['likelihood_level']}, {result['consequence_level']}"),
            ("Prioridad de inspección", result["inspection_priority"]),
            ("Banda Df", result["damage_factor_band"]),
            ("Base", result["reference"]),
        )
    )
    hide_message()


def render_all_selects():
    equipment_options = [(item["id"], f"{item['id']} · {item['name']}") for item in DATA["equipment"]]
    fill_select("#equipment-select", equipment_options)
    fill_select("#schematic-equipment", equipment_options)
    fill_select("#rbi-equipment", equipment_options)
    fill_select("#measurement-point", all_point_options())


def show_view(view_name):
    for name in ("dashboard", "equipment", "schematic", "measurements", "rbi", "project"):
        document.querySelector(f"#view-{name}").hidden = name != view_name
        button = document.querySelector(f'.nav-button[data-view="{name}"]')
        button.className = "nav-button active" if name == view_name else "nav-button"
    if view_name == "dashboard":
        render_dashboard()
    elif view_name == "schematic":
        render_schematic()
    elif view_name == "measurements":
        render_measurement()
    elif view_name == "rbi":
        render_rbi()


def bind_events():
    def listen(selector, event_name, callback):
        proxy = create_proxy(callback)
        EVENT_PROXIES.append(proxy)
        document.querySelector(selector).addEventListener(event_name, proxy)

    for name in ("dashboard", "equipment", "schematic", "measurements", "rbi", "project"):
        listen(f'.nav-button[data-view="{name}"]', "click", view_handler(name))
    listen('[data-go="equipment"]', "click", view_handler("equipment"))
    for selector in ("#filter-family", "#filter-condition"):
        listen(selector, "change", lambda event: render_dashboard())
    listen("#filter-location", "input", lambda event: render_dashboard())
    listen("#equipment-table", "click", on_table_click)
    listen("#schematic-equipment", "change", lambda event: render_schematic())
    listen("#measurement-point", "change", lambda event: render_measurement())
    listen("#rbi-equipment", "change", lambda event: render_rbi())
    listen("#rbi-form", "submit", lambda event: (event.preventDefault(), render_rbi()))
    listen("#equipment-select", "change", on_equipment_select)
    listen("#new-equipment", "click", start_new_equipment)
    listen("#equipment-form", "submit", on_save_equipment)
    listen("#cml-list", "click", on_cml_list_click)
    listen("#measurement-history", "click", on_measurement_history_click)
    listen("#schematic-canvas", "click", on_point_click)
    listen("#schematic-image-upload", "change", on_schematic_image_upload)
    listen("#schematic-generated", "click", show_generated_schematic)
    listen("#toggle-cml-form", "click", toggle_cml_form)
    listen("#cml-form", "submit", on_save_cml)
    listen("#measurement-form", "submit", on_save_measurement)
    listen("#export-data", "click", export_data)
    listen("#import-data", "change", import_data)
    listen("#reset-data", "click", reset_data)


def view_handler(name):
    def handle(_event):
        show_view(name)

    return handle


def on_table_click(event):
    edit_id = event.target.closest("[data-edit]")
    measure_id = event.target.closest("[data-measure]")
    if edit_id:
        document.querySelector("#equipment-select").value = edit_id.getAttribute("data-edit")
        on_equipment_select(None)
        show_view("equipment")
    elif measure_id:
        equipment = equipment_by_id(measure_id.getAttribute("data-measure"))
        options = [(f"{equipment['id']}::{point['id']}", f"{equipment['name']} · {point['id']}") for point in equipment.get("cmls", [])]
        selected = fill_select("#measurement-point", options)
        show_view("measurements")
        document.querySelector("#measurement-point").value = selected
        render_measurement()


def on_point_click(event):
    point_element = event.target.closest("[data-point]")
    if point_element:
        document.querySelector("#measurement-point").value = point_element.getAttribute("data-point")
        show_view("measurements")


def toggle_cml_form(event):
    form = document.querySelector("#cml-form")
    if form.getAttribute("data-editing-id") is not None:
        reset_cml_form(form)
        form.hidden = False
        return
    form.hidden = not form.hidden


def reset_cml_form(form):
    form.reset()
    form.removeAttribute("data-editing-id")
    form.querySelector('button[type="submit"]').textContent = "Guardar punto"
    document.querySelector("#toggle-cml-form").textContent = "＋ Añadir CML/TML"


def on_cml_list_click(event):
    delete_button = event.target.closest("[data-delete-cml]")
    if delete_button:
        delete_cml_point(delete_button.getAttribute("data-delete-cml"))
        return

    edit_button = event.target.closest("[data-edit-cml]")
    if edit_button:
        edit_cml_point(edit_button.getAttribute("data-edit-cml"))
        return

    on_point_click(event)


def edit_cml_point(point_key):
    equipment_id, point_id = point_key.split("::", 1)
    equipment = equipment_by_id(equipment_id)
    point = point_by_id(equipment, point_id) if equipment else None
    if equipment is None or point is None:
        show_message("No se encontró el punto CML/TML que desea editar.", error=True)
        return

    document.querySelector("#schematic-equipment").value = equipment_id
    document.querySelector("#cml-id").value = point["id"]
    document.querySelector("#cml-description").value = point.get("description", "")
    document.querySelector("#cml-x").value = point.get("x", 50)
    document.querySelector("#cml-y").value = point.get("y", 50)
    form = document.querySelector("#cml-form")
    form.setAttribute("data-editing-id", point["id"])
    form.querySelector('button[type="submit"]').textContent = "Guardar cambios"
    document.querySelector("#toggle-cml-form").textContent = "＋ Añadir CML/TML"
    form.hidden = False


def delete_cml_point(point_key):
    equipment_id, point_id = point_key.split("::", 1)
    equipment = equipment_by_id(equipment_id)
    point = point_by_id(equipment, point_id) if equipment else None
    if equipment is None or point is None:
        show_message("No se encontró el punto CML/TML que desea eliminar.", error=True)
        return

    equipment["cmls"].remove(point)
    save_data()
    render_all_selects()
    document.querySelector("#schematic-equipment").value = equipment_id
    render_schematic()
    render_dashboard()
    render_measurement()
    render_rbi()
    form = document.querySelector("#cml-form")
    if form.getAttribute("data-editing-id") == point_id:
        reset_cml_form(form)
        form.hidden = True
    show_message(f"Punto CML/TML {point_id} eliminado.")


def on_save_cml(event):
    event.preventDefault()
    equipment = equipment_by_id(document.querySelector("#schematic-equipment").value)
    if equipment is None:
        show_message("Seleccione un equipo antes de agregar un punto.", error=True)
        return
    form = document.querySelector("#cml-form")
    editing_id = form.getAttribute("data-editing-id")
    point_id = document.querySelector("#cml-id").value.strip()
    if not point_id:
        show_message("El ID del punto CML/TML no puede estar vacío.", error=True)
        return
    if any(
        point["id"] == point_id and point["id"] != editing_id
        for point in equipment.get("cmls", [])
    ):
        show_message(f"El punto {point_id} ya existe en este equipo.", error=True)
        return
    try:
        x = float(document.querySelector("#cml-x").value)
        y = float(document.querySelector("#cml-y").value)
        if not (0 <= x <= 100 and 0 <= y <= 100):
            raise ValueError("Las coordenadas X/Y deben estar entre 0 y 100.")
    except ValueError as exc:
        show_message(f"Coordenadas inválidas: {exc}", error=True)
        return
    description = document.querySelector("#cml-description").value.strip()
    if editing_id is not None:
        point = point_by_id(equipment, editing_id)
        if point is None:
            show_message(f"No se encontró el punto CML/TML {editing_id} para guardar los cambios.", error=True)
            return
        selected_measurement = document.querySelector("#measurement-point").value
        point["id"] = point_id
        point["description"] = description
        point["x"] = x
        point["y"] = y
        if selected_measurement == f"{equipment['id']}::{editing_id}":
            document.querySelector("#measurement-point").value = f"{equipment['id']}::{point_id}"
    else:
        equipment.setdefault("cmls", []).append({
            "id": point_id,
            "description": description,
            "x": x,
            "y": y,
            "measurements": [],
        })
    save_data()
    reset_cml_form(form)
    form.hidden = True
    render_all_selects()
    document.querySelector("#schematic-equipment").value = equipment["id"]
    render_schematic()
    if editing_id is not None:
        render_dashboard()
        render_measurement()
        render_rbi()
        show_message(f"Punto CML/TML {point_id} actualizado.")
    else:
        show_message(f"Punto {point_id} agregado. Registre sus campañas UT en Mediciones.")


def on_measurement_history_click(event):
    delete_button = event.target.closest("[data-delete-measurement]")
    if delete_button is None:
        return

    try:
        measurement_index = int(delete_button.getAttribute("data-delete-measurement"))
    except (TypeError, ValueError):
        show_message("El índice de la medición seleccionada no es válido.", error=True)
        return

    value = document.querySelector("#measurement-point").value
    if not value:
        show_message("Seleccione un punto CML/TML antes de eliminar una medición.", error=True)
        return
    equipment_id, point_id = value.split("::", 1)
    equipment = equipment_by_id(equipment_id)
    point = point_by_id(equipment, point_id) if equipment else None
    measurements = point.get("measurements", []) if point else []
    if equipment is None or point is None or not 0 <= measurement_index < len(measurements):
        show_message("La medición seleccionada ya no existe.", error=True)
        return

    removed = measurements.pop(measurement_index)
    save_data()
    render_measurement()
    render_dashboard()
    render_schematic()
    render_rbi()
    show_message(f"Medición del {removed['date']} eliminada del punto {point_id}.")


def on_save_measurement(event):
    event.preventDefault()
    value = document.querySelector("#measurement-point").value
    if not value:
        show_message("Seleccione un punto CML/TML antes de registrar una medición.", error=True)
        return
    equipment_id, point_id = value.split("::", 1)
    equipment = equipment_by_id(equipment_id)
    point = point_by_id(equipment, point_id) if equipment else None
    if equipment is None or point is None:
        show_message("El equipo o punto seleccionado ya no existe.", error=True)
        return
    measurement_date = document.querySelector("#measurement-date").value
    try:
        measured = float(document.querySelector("#measurement-thickness").value)
        if not measurement_date or measured <= 0:
            raise ValueError("La fecha y un espesor positivo son obligatorios.")
        if point.get("measurements"):
            last_date = date.fromisoformat(point["measurements"][-1]["date"])
            if date.fromisoformat(measurement_date) <= last_date:
                raise ValueError("La nueva fecha debe ser posterior a la última campaña del punto.")
    except (ValueError, KeyError) as exc:
        show_message(f"No se registró la medición: {exc}", error=True)
        return
    point.setdefault("measurements", []).append({
        "date": measurement_date,
        "thickness_mm": measured,
        "reset_baseline": document.querySelector("#measurement-reset").checked,
    })
    save_data()
    document.querySelector("#measurement-form").reset()
    document.querySelector("#measurement-date").value = date.today().isoformat()
    render_measurement()
    render_dashboard()
    render_schematic()
    show_message(f"Medición de {point_id} registrada.")


def on_equipment_select(event):
    equipment = equipment_by_id(document.querySelector("#equipment-select").value)
    if equipment:
        populate_equipment_form(equipment)


def start_new_equipment(event):
    document.querySelector("#equipment-select").value = ""
    document.querySelector("#equipment-name").value = ""
    document.querySelector("#equipment-location").value = ""
    document.querySelector("#equipment-material").value = ""
    document.querySelector("#equipment-family").value = "pipe"
    defaults = {
        "design_pressure_mpa": 1.0, "outside_diameter_mm": 100, "inside_radius_mm": 500,
        "allowable_stress_mpa": 138, "weld_efficiency": 1, "weld_strength_reduction": 1,
        "coefficient_y": 0.4, "tank_diameter_m": 20, "liquid_height_m": 10,
        "specific_gravity": 1, "nominal_thickness_mm": 10, "mill_tolerance_fraction": 0.125,
        "corrosion_allowance_mm": 1, "inspection_class_max_years": 5,
    }
    for key in FIELD_KEYS:
        document.querySelector(f'[data-field="{key}"]').value = defaults.get(key, "")
    document.querySelector("#equipment-design-summary").textContent = "Complete los datos para guardar el nuevo activo."
    show_view("equipment")


def on_save_equipment(event):
    event.preventDefault()
    name = document.querySelector("#equipment-name").value.strip()
    location = document.querySelector("#equipment-location").value.strip()
    family = document.querySelector("#equipment-family").value
    if not name or not location:
        show_message("Identificación y ubicación técnica son obligatorias.", error=True)
        return
    equipment_id = document.querySelector("#equipment-select").value
    current = equipment_by_id(equipment_id) if equipment_id else None
    values = {}
    try:
        for key in FIELD_KEYS:
            raw = document.querySelector(f'[data-field="{key}"]').value.strip()
            if raw:
                values[key] = float(raw)
        record = {
            **(current or {}),
            "id": equipment_id or f"EQ-{int(time.time() * 1000)}",
            "name": name, "location": location, "family": family,
            "material_specification": document.querySelector("#equipment-material").value.strip(),
            **values,
        }
        family_calculation(record)
    except (ValueError, KeyError, TypeError) as exc:
        show_message(f"Revise los campos de diseño: {exc}", error=True)
        return
    if current:
        current.update(record)
    else:
        record["cmls"] = []
        record["schematic_id"] = family
        DATA["equipment"].append(record)
    save_data()
    render_all_selects()
    document.querySelector("#equipment-select").value = record["id"]
    populate_equipment_form(record)
    render_dashboard()
    show_message(f"Equipo {record['id']} guardado localmente.")


def export_data(event):
    payload = json.dumps(DATA, ensure_ascii=False, indent=2)
    blob = Blob.new([payload], {"type": "application/json;charset=utf-8"})
    url = URL.createObjectURL(blob)
    anchor = document.createElement("a")
    anchor.href = url
    anchor.download = "integra-proyecto.json"
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
    show_message("JSON de proyecto exportado.")


def import_data(event):
    file_list = event.currentTarget.files
    if file_list.length == 0:
        return
    selected_file = file_list.item(0)
    event.currentTarget.value = ""
    reader = FileReader.new()

    def on_load(_event):
        try:
            imported = json.loads(str(reader.result))
            validate_project(imported)
            global DATA
            DATA = imported
            save_data()
            render_all_selects()
            render_dashboard()
            if DATA["equipment"]:
                populate_equipment_form(DATA["equipment"][0])
            render_schematic()
            render_measurement()
            render_rbi()
            show_message("Proyecto JSON importado y guardado en este navegador.")
        except (ValueError, TypeError, KeyError) as exc:
            show_message(f"No se pudo importar el archivo: {exc}", error=True)

    proxy = create_proxy(on_load)
    EVENT_PROXIES.append(proxy)
    reader.addEventListener("load", proxy)
    error_proxy = create_proxy(
        lambda _event: show_message("No se pudo leer el archivo JSON.", error=True)
    )
    EVENT_PROXIES.append(error_proxy)
    reader.addEventListener("error", error_proxy)
    reader.readAsText(selected_file)


def reset_data(_event):
    asyncio.ensure_future(reset_demo())


async def reset_demo():
    response = await fetch("./datos_demo.json")
    if not response.ok:
        show_message(f"No se pudo leer datos_demo.json (HTTP {response.status}).", error=True)
        return
    global DATA
    DATA = json.loads(await response.text())
    validate_project(DATA)
    save_data()
    render_all_selects()
    render_dashboard()
    show_message("Se restauraron los datos demo.")


async def load_project():
    global DATA
    saved = localStorage.getItem(STORAGE_KEY)
    if saved:
        DATA = json.loads(saved)
    else:
        response = await fetch("./datos_demo.json")
        if not response.ok:
            raise RuntimeError(f"No se pudo cargar datos_demo.json (HTTP {response.status}).")
        DATA = json.loads(await response.text())
    validate_project(DATA)
    if not saved:
        save_data()


DATA = {"equipment": []}


async def initialize():
    await load_project()
    bind_events()
    render_all_selects()
    document.querySelector("#measurement-date").value = date.today().isoformat()
    saved_rbi = DATA.get("rbi", {})
    for control_id, key in (
        ("#rbi-age", "service_age_years"),
        ("#rbi-base-frequency", "base_failure_frequency_per_year"),
        ("#rbi-management-factor", "management_factor"),
        ("#rbi-area", "consequence_area_m2"),
        ("#rbi-economic", "economic_consequence"),
    ):
        if key in saved_rbi:
            document.querySelector(control_id).value = saved_rbi[key]
    if saved_rbi.get("equipment_id"):
        document.querySelector("#rbi-equipment").value = saved_rbi["equipment_id"]
    if saved_rbi.get("currency") in ("USD", "CLP"):
        document.querySelector("#rbi-currency").value = saved_rbi["currency"]
    render_dashboard()
    if DATA["equipment"]:
        populate_equipment_form(DATA["equipment"][0])
    render_schematic()
    render_measurement()
    render_rbi()


asyncio.ensure_future(initialize())
