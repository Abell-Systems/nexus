"""Parses a real INVENES detail-page HTML record into the generic OEPM JSON item
shape already consumed by application.ingestion.normalizers.oepm_normalizer
.OepmNormalizer (reused unmodified -- ADR 0035 SS11.3 explicitly does not
redesign it).

Field regexes were derived directly from three real fetched records
(data/raw/oepm_invenes_sample/*.html): a national patent, a utility model, and
an EP-ES (T3) validation -- not a guess at the page's structure.
"""

import re
from dataclasses import dataclass
from typing import Any

_TITLE_RE = re.compile(r'datosBibliograficos".*?<b>(.*?)<br', re.S)
_PUBNUM_RE = re.compile(
    r"N[uú]mero de publicaci[oó]n:.*?>([A-Z]{2}\d+)</a>&nbsp;([A-Z]\d?)&nbsp;\((\d{2}\.\d{2}\.\d{4})\)",
    re.S,
)
_APPNUM_RE = re.compile(
    r"N[uú]mero de Solicitud:.*?&nbsp;([A-Za-z0-9/.]+)\s*&nbsp;\((\d{2}\.\d{2}\.\d{4})\)",
    re.S,
)
_SOLICITANTE_RE = re.compile(r"Solicitante:.*?<td><span[^>]*>(.*?)</span></td>", re.S)
_INVENTOR_RE = re.compile(r"Inventor/es:.*?<td><span[^>]*>(.*?)</span></td>", re.S)
_CIP_BLOCK_RE = re.compile(
    r'Clasificaci[oó]n Internacional de Patentes\s*">CIP:</acronym>(.*?)</table>\s*</td>\s*</tr>\s*</table>',
    re.S,
)
_CIP_CODE_RE = re.compile(r">([A-Z]\d{2}[A-Z]\s?\d+/\d+)<")
_CPC_HREF_RE = re.compile(r'CPC=([A-Z0-9/]+)"')
_RESUMEN_RE = re.compile(r"Resumen:.*?<img[^>]*>(.*?)</span>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_PERSON_ENTRY_RE = re.compile(r"^(.*?)\s*\([A-Z]{2}\)\s*;?$")
_ASSIGNEE_LINE_RE = re.compile(r"^(.*?)\s*\([\d.]+%\)\s*\([A-Z]{2}\)$")
_BR_SPLIT_RE = re.compile(r"<br\s*/?>", re.I)


def _clean(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def _split_assignees(raw: str) -> list[str]:
    """Each applicant appears as its own "NAME (OWNERSHIP%) (CC)" line, followed
    by an address line -- <br>-split first so the address (which never matches
    the ownership-percent pattern) is discarded rather than swallowed into the name."""
    names: list[str] = []
    for line in _BR_SPLIT_RE.split(raw):
        cleaned = _clean(line)
        if not cleaned:
            continue
        m = _ASSIGNEE_LINE_RE.match(cleaned)
        if m:
            names.append(m.group(1).strip())
    return names


def _split_people(raw: str) -> list[str]:
    cleaned = _clean(raw)
    names: list[str] = []
    for chunk in cleaned.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = _PERSON_ENTRY_RE.match(chunk)
        names.append(m.group(1).strip() if m else chunk)
    return names


@dataclass(frozen=True)
class ParsedInvenesRecord:
    item: dict[str, Any]
    kind_code: str


def parse_invenes_detail(html_bytes: bytes, referencia: str) -> ParsedInvenesRecord | None:
    """Returns None if the page does not contain a recognizable bibliographic
    record (parse failure -- caller should QUARANTINE, not silently drop)."""
    try:
        html = html_bytes.decode("windows-1252")
    except UnicodeDecodeError:
        html = html_bytes.decode("utf-8", errors="replace")

    pubnum_m = _PUBNUM_RE.search(html)
    title_m = _TITLE_RE.search(html)
    if not pubnum_m or not title_m:
        return None

    pub_prefix, kind_code, pub_date_raw = pubnum_m.groups()
    doc_number = pub_prefix[2:]
    country_code = pub_prefix[:2]
    publication_id = f"{country_code}{doc_number}{kind_code}"

    app_m = _APPNUM_RE.search(html)
    application_number, filing_date_raw = app_m.groups() if app_m else (None, None)

    solicitante_m = _SOLICITANTE_RE.search(html)
    assignees = _split_assignees(solicitante_m.group(1)) if solicitante_m else []

    inventor_m = _INVENTOR_RE.search(html)
    inventors = _split_people(inventor_m.group(1)) if inventor_m else []

    cip_block_m = _CIP_BLOCK_RE.search(html)
    classifications_ipc = _CIP_CODE_RE.findall(cip_block_m.group(1)) if cip_block_m else []
    classifications_cpc = _CPC_HREF_RE.findall(html)

    resumen_m = _RESUMEN_RE.search(html)
    abstract = _clean(resumen_m.group(1)) if resumen_m else ""

    item = {
        "publication_id": publication_id,
        "country_code": country_code,
        "doc_number": doc_number,
        "kind_code": kind_code,
        "application_number": application_number,
        "title": _clean(title_m.group(1)),
        "abstract": abstract,
        "assignees": assignees,
        "inventors": inventors,
        "filing_date": _ddmmyyyy_to_iso(filing_date_raw),
        "publication_date": _ddmmyyyy_to_iso(pub_date_raw),
        "classifications_cpc": classifications_cpc,
        "classifications_ipc": classifications_ipc,
        "invenes_url": f"https://consultas2.oepm.es/InvenesWeb/detalle?referencia={referencia}",
    }
    return ParsedInvenesRecord(item=item, kind_code=kind_code)


def _ddmmyyyy_to_iso(raw: str | None) -> str | None:
    if not raw:
        return None
    dd, mm, yyyy = raw.split(".")
    return f"{yyyy}-{mm}-{dd}"
