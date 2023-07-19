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
corresponding to this element.  You can use this to match the element
to words or characters using the API described below.

There are a number of other fields which may be present, but probably
are not, including `id`, `title`, `alt_text`, and `actual_text`.
Support for these is uncertain until I find some PDFs that actually
contain them.

Likewise, attributes for structure elements (which, confusingly, come
as a *list* of dictionaries) are not supported because I haven't got a
PDF using them to test with yet.

# Marked Content Sections

The structure of a PDF obviously isn't all that useful unless you can,
minimally, attach some text to the elements.  This is where marked
content sections come in.

`pdfplumber` adds an optional field called `mcid` to the items in the
`objects` and `chars` properties of a page, which tells you which
marked content section a given character or other object belongs to.

You can propagate `mcid` to the words returned by `extract_words` by
adding it to the `extra_attrs` argument, e.g.:


    words = pdf.pages[0].extract_words(extra_attrs=["mcid"])
