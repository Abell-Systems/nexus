_GOOGLE = "https://patents.google.com/patent/"
_ESPACENET = "https://worldwide.espacenet.com/patent/search?q=pn%3D"


def source_links(publication_id: str) -> dict[str, str]:
    compact = publication_id.replace("-", "")
    return {"google_patents": f"{_GOOGLE}{compact}", "espacenet": f"{_ESPACENET}{compact}"}
