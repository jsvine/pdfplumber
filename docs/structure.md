# Structure Tree

Since PDF 1.3 it is possible for a PDF to contain logical structure,
contained in a *structure tree*.  In conjunction with PDF 1.2 [marked
content sections](#marked-content-sections) this forms the basis of
Tagged PDF and other accessibility features.

Unfortunately, since all of these standards are optional and variably
implemented in PDF authoring tools, and are frequently not enabled by
default, it is not possible to rely on them to extract the structure
of a PDF and associated content.  Nonetheless they can be useful as
features for a heuristic or machine-learning based system, or for
extracting particular structures such as tables.

Since `pdfplumber`'s API is page-based, the structure is available for
a particular page, using the `structure_tree` attribute:

    with pdfplumber.open(pdffile) as pdf:
        for element in pdf.pages[0].structure_tree:
             print(element["type"], element["mcids"])
             for child in element.children:
                 print(child["type"], child["mcids"])

The `type` field contains the type of the structure element - the
standard structure types can be seen in section 10.7.3 of [the PDF 1.7
reference
document](https://ghostscript.com/~robin/pdf_reference17.pdf#page=898),
but usually they are rather HTML-like, if created by a recent PDF
authoring tool (notably, older tools may simply produce `P` for
everything).

The `mcids` field contains the list of marked content section IDs
corresponding to this element.

The `lang` field is often present as well, and contains a language
code for the text content, e.g. `"EN-US"` or `"FR-CA"`.

The `alt_text` field will be present if the author has helpfully added
alternate text to an image.  In some cases, `actual_text` may also be
present.

There are also various attributes that may be in the `attributes`
field.  Some of these are quite useful indeed, such as ``BBox` which
gives you the bounding box of a `Table`, `Figure`, or `Image`.  You
can see a full list of these [in the PDF
spec](https://ghostscript.com/~robin/pdf_reference17.pdf#page=916).
Note that the `BBox` is in PDF coordinate space with the origin at the
bottom left of the page.  To convert it to `pdfplumber`'s space you
can do, for example:

    x0, y0, x1, y1 = element['attributes']['BBox']
    top = page.height - y1
    bottom = page.height - y0
    doctop = page.initial_doctop + top
    bbox = (x0, top, x1, bottom)

It is also possible to get the structure tree for the entire document.
In this case, because marked content IDs are specific to a given page,
each element will also have a `page_number` attribute, which is the
number of the page containing (partially or completely) this element,
indexed from 1 (for consistency with `pdfplumber.Page`).

You can also access the underlying `PDFStructTree` object for more
flexibility, including visual debugging.  For instance to plot the
bounding boxes of the contents of all of the `TD` elements on the
first page of a document:

    page = pdf.pages[0]
    stree = PDFStructTree(pdf, page)
    img = page.to_image()
    img.draw_rects(stree.element_bbox(td) for td in table.find_all("TD"))

The `find_all` method works rather like the same method in
[BeautifulSoup](https://beautiful-soup-4.readthedocs.io/en/latest/#searching-the-tree) -
it takes an element name, a regular expression, or a matching
function.
