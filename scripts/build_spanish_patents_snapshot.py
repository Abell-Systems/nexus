import sys
from pathlib import Path

# Add project root to sys.path if needed
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.patent_agent.tools.duckdb_patents import DuckDbPatentsDataSource
from backend.patent_agent.tools.schemas import PatentRecord

SAMPLE_ES_PATENTS = [
    # C11D - Detergents / Chemistry
    PatentRecord(
        publication_number="ES-2849102-B2",
        title="Formulación detergente enzimática líquida biodegradable para lavado textil a temperatura ambiente",
        abstract="Composición de detergente líquido basada en ésteres de ácidos grasos y enzimas proteolíticas activas entre 15-25°C con baja huella de carbono.",
        assignee="Laboratorios Bilper S.A.",
        filing_date="2020-05-12",
        cpc_codes=["C11D1/00", "C11D3/386", "C11D3/20"],
        citation_count=6,
    ),
    PatentRecord(
        publication_number="ES-2715482-A1",
        title="Procedimiento de microencapsulación de fragancias estables en formulaciones detergentes acuosas",
        abstract="Método para encapsular aceites esenciales en matrices poliméricas biocompatibles para liberación prolongada.",
        assignee="Consejo Superior de Investigaciones Científicas (CSIC)",
        filing_date="2018-09-10",
        cpc_codes=["C11D3/50", "B01J13/02"],
        citation_count=12,
    ),
    # E03C / A47J - Smart Sanitary / Sinks
    PatentRecord(
        publication_number="ES-2684913-A1",
        title="Fregadero modular con sistema integrado de recirculación y desinfección de aguas grises",
        abstract="Dispositivo sanitario de cocina que incorpora filtrado por etapas y sensorización de consumo hídrico.",
        assignee="Roca Sanitario S.A.",
        filing_date="2017-03-22",
        cpc_codes=["E03C1/18", "E03C1/04", "C02F1/00"],
        citation_count=14,
    ),
    PatentRecord(
        publication_number="ES-2901234-A1",
        title="Grifería electrónica con sensorización óptica de caudal y mezcla térmica instantánea",
        abstract="Válvula mezcladora inteligente para instalaciones domésticas con conectividad Bluetooth/Zigbee.",
        assignee="Teka Industrial S.A.",
        filing_date="2022-01-18",
        cpc_codes=["E03C1/05", "G05D23/13"],
        citation_count=3,
    ),
    # G05B / H02J - IoT & Energy Management
    PatentRecord(
        publication_number="ES-2895412-B1",
        title="Sistema ciberfísico para optimización del consumo eléctrico en líneas de manufactura continua mediante gemelo digital",
        abstract="Arquitectura IoT industrial con modelos predictivos de consumo energético y detección temprana de anomalías en motores.",
        assignee="Universidad Politécnica de Madrid / Mondragon Corp",
        filing_date="2021-11-04",
        cpc_codes=["G05B19/418", "G05B23/02", "H02J13/00"],
        citation_count=8,
    ),
    PatentRecord(
        publication_number="ES-2765431-A1",
        title="Dispositivo de monitorización no intrusiva de cargas eléctricas industriales (NILM)",
        abstract="Algoritmo y hardware para desagregación de consumos en cuadros de distribución industrial.",
        assignee="Circutor S.A.",
        filing_date="2019-06-30",
        cpc_codes=["G01R31/00", "G05B17/02", "H02J3/00"],
        citation_count=19,
    ),
    # C22C - Metallurgy (Lead-free alloys)
    PatentRecord(
        publication_number="ES-2654981-A1",
        title="Aleación de latón libre de plomo con adición de bismuto y silicio de alta maquinabilidad",
        abstract="Aleación ecológica de cobre-zinc con aditivos para fragmentación de viruta en decoletaje de precisión.",
        assignee="Universidad del País Vasco (UPV/EHU)",
        filing_date="2017-10-15",
        cpc_codes=["C22C9/04", "B23B1/00"],
        citation_count=15,
    )
]

def main():
    snapshot_path = "data/snapshots/patents_es_snapshot.duckdb"
    ds = DuckDbPatentsDataSource(db_path=snapshot_path)
    # Add publication dates and backward citations to sample
    for p in SAMPLE_ES_PATENTS:
        setattr(p, "publication_date", p.filing_date)
        setattr(p, "backward_citation_count", max(3, p.citation_count // 2))
    ds.insert_patents(SAMPLE_ES_PATENTS)
    print(f"✅ Populated DuckDB snapshot at {snapshot_path} with {len(SAMPLE_ES_PATENTS)} ES patents.")

if __name__ == "__main__":
    main()
