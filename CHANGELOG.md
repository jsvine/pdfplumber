# Change Log

All notable changes to this project will be documented in this file. Currently goes back to `v0.4.3`.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

## [0.6.0-alpha] — 2018-02-05
### Added
- Color information for many objects, thanks to `pdfminer.six` updates
- Font size and name to results of `Page/utils.extract_words`; `match_fontsize`, `match_fontname`, and `fontsize_tolerance` keyword arguments to that method.
- Ability for `Page.crop`/etc. to accept rects and other `pdfplumber` objects
- `PageImage.draw_object`, which tries to replicate a given object's attributes
- `Page.find_text_edges`, which returns a list of lines that appear to define implicit borders/edges/alignment
- `char_threshold` argument for `Page.crop`, which lets you decide how much of a `char` needs to be within a cropping box to be retained
- `MANIFEST.in`
- `requirements.txt`
  
### Changed
- Big revamp/simplification of table extraction
- Upgrade to `pdfminer.six==20170419`

### Fixed
- Fix `utils.objects_overlap`, which was failing when the second object was entirely encompassing first object

### Deprecated
- Access to `Page.annos`, which wasn't actually working in the first place. Hoping to re-add proper support.
- Access to `y0` and `y1` properties, which were redundant and a bit confusing
- utils.resize_object, which contained flawed assumptions and wasn't necessary

## [0.5.7] — 2018-01-20
### Added
- `.travis.yml`, but failing on `.to_image()`

### Changed
- Move from defunct `pycrypto` to `pycryptodome`
- Update `pdfminer.six` to `20170720`

## [0.5.6] — 2017-11-21
### Fixed
- Fix issue #41, in which PDF-object-referenced cropboxes/mediaboxes weren't being fully resolved.

## [0.5.5] — 2017-05-10
### Added
- Access to `__version__` from main namespace

### Fixed
- Fix issue #33, by checking `decode_text`'s argument type

## [0.5.4] — 2017-04-27
### Fixed
- Pin `pdfminer.six` to version `20151013` (for now), fixing incompatibility

## [0.5.3] — 2017-02-27
### Fixed
- Allow `import pdfplumber` even if ImageMagick not installed.

## [0.5.2] — 2017-02-27
### Added
- Access to `curve` points. (E.g., `page.curves[0]["points"]`.)
- Ability for `.draw_line` to draw `curve` points.

### Changed
- Disaggregated "min_words_vertical" (default: 3) and "min_words_horizontal" (default: 1), removing "text_word_threshold".
- Internally, made `utils.decimalize` a bit more robust; now throws errors on non-decimalizable items.
- Now explicitly ignoring some (obscure) `pdfminer` object attributes.
- Raw input for `.draw_line` from a bounding box to `((x, y), (x, y))`, for consistency with `curve["points"]` and with `Pillow`'s underlying method.

### Fixed
- Fixed typo bug when `.rect_edges` is called before `.edges`

## [0.5.1] — 2017-02-26
### Added
- Quick-draw `PageImage` methods: `.draw_vline`, `.draw_vlines`, `.draw_hline`, and `.draw_hlines`.
- Boolean parameter `keep_blank_chars` for `.extract_words(...)` and `TableFinder` settings.

### Changed
- Increased default `text_tolerance` and `intersection_tolerance` TableFinder values from 1 to 3.

### Fixed
- Properly handle conversion of PDFs with transparency to `pillow` images.
- Properly handle `pandas` DataFrames as inputs to multi-draw commands (e.g., `PageImage.draw_rects(...)`).

## [0.5.0] - 2017-02-25
### Added
- Visual debugging features, via `Page.to_image(...)` and `PageImage`. (Introduces `wand` and `pillow` as package requirements.)
- More powerful options for extracting data from tables. See changes below.

### Changed
- Entirely overhaul the table-extraction methods. Now based on [Anssi Nurminen's master's thesis](http://dspace.cc.tut.fi/dpub/bitstream/handle/123456789/21520/Nurminen.pdf?sequence=3).
- Disentangle `.crop` from `.intersects_bbox` and `.within_bbox`.
- Change default `x_tolerance` and `y_tolerance` for word extraction from `5` to `3`

### Fixed
- Fix bug stemming from non-decimalized page heights. [h/t @jsfenfen]

## [0.4.6] - 2017-01-26
### Added
- Provide access to `Page.page_number`

### Changed
- Use `.page_number` instead of `.page_id` as primary identifier. [h/t @jsfenfen]
- Change default `x_tolerance` and `y_tolerance` for word extraction from `0` to `5`

### Fixed
- Provide proper support for rotated pages

## [0.4.5] - 2016-12-09
### Fixed
- Fix bug stemming from when metadata includes a PostScript literal. [h/t @boblannon]


## [0.4.4] - Mistakenly skipped

Whoops.

## [0.4.3] - 2016-04-12
### Changed
- When extracting table cells, use chars' midpoints instead of top-points.

### Fixed
- Fix find_gutters — should ignore `" "` chars
