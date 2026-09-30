from infrastructure.operational.links import source_links


class SourceLinksTest:
    def test_should_build_google_and_espacenet_links_when_publication_is_spanish(self):
        links = source_links("ES-2594181-A1")
        assert links["google_patents"] == "https://patents.google.com/patent/ES2594181A1"
        assert links["espacenet"] == "https://worldwide.espacenet.com/patent/search?q=pn%3DES2594181A1"

    def test_should_build_links_when_publication_is_european(self):
        assert source_links("EP-3000000-B1")["google_patents"] == "https://patents.google.com/patent/EP3000000B1"
