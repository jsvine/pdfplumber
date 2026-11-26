from pathlib import Path

import pdfplumber


def test_readme_matches_uri_hyperlinks_to_table_cells():
    here = Path(__file__).resolve().parent
    readme = (here.parent / "README.md").read_text(encoding="utf-8")
    section = readme.split("#### Matching URI hyperlinks to table cells", 1)
    assert len(section) == 2, "The README hyperlink example is missing"
    example = section[1].split("```python\n", 1)[1].split("\n```", 1)[0]

    span_uri = "https://example.com/span"
    border_uri = "https://example.com/border"
    outside_uri = "https://example.com/outside"
    with pdfplumber.open(here / "pdfs" / "table-uri-links.pdf") as pdf:
        page = pdf.pages[0]
        links = {link["uri"]: link for link in page.hyperlinks}
        assert set(links) == {span_uri, border_uri, outside_uri}
        border = links[border_uri]
        assert border["x0"] < 140 < border["x1"]
        assert (border["x0"] + border["x1"]) / 2 == 140
        table = page.find_tables()[0]
        assert table.rows[0].cells == [(40, 40, 240, 80), None]
        assert table.rows[1].cells == [(40, 80, 140, 120), (140, 80, 240, 120)]

        scope = {"page": page}
        exec(compile(example, "README.md", "exec"), scope)

    assert scope["tables"] == [
        [
            [{"text": "Spanning cell", "uris": [span_uri]}, None],
            [{"text": "Left", "uris": []}, {"text": "Right", "uris": [border_uri]}],
        ]
    ]
