# Change Log

All notable changes to this project will be documented in this file. Currently goes back to `v0.4.3`.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

## [0.5.21] — 2020-05-27
### Fixed
- Fix `Page.extract_table(...)` to return `None` instead of crashing when no table is found (d64afa8) [h/t @stucka]

## [0.5.20] — 2020-04-29
### Fixed
- Fix `.get_page_image` to prefer paths over streams, when possible (ab957de) [h/t @ubmarco]
- Local-fix pdfminer.six's `.resolve_all` to handle tuples and simplify (85f422d)

### Changed
- Remove support for Python 2 and Python <3.3

## [0.5.19] — 2020-04-16
### Changed
- Add `utils.decimalize` performance improvement (830d117) [h/t @ubmarco]

### Fixed
- Fix un-referenced method when using "text" table-finding strategy (2a0c4a2c)
- Add missing object type `rect_edge` to `obj_to_edges()` (0edc6bfa)

## [0.5.18] — 2020-04-01
### Changed
- Allow `rect` and `curve` objects also to be passed to "explicit_..._lines" setting when table-finding. (And disallow other types of dicts to be passed.)

### Fixed
- Fix `utils.extract_text` bug introduced in prior version

## [0.5.17] — 2020-04-01
### Fixed
- Fix and simplify obj-in-bbox logic (see commit 25672961)
- Improve/fix the way `utils.extract_text` handles vertical text (see commit 8a5d858b) [h/t @dwalton76]
- Have `Page.to_image` use bytes stream instead of file path (Issue #124 / PR #179) [h/t @cheungpat]
- Fix issue #176, in which `Page.extract_tables` did not pass kwargs to `Table.extract` [h/t @jsfenfen]

## [0.5.16] — 2020-01-12
### Fixed
- Prevent custom LAParams from raising exception (Issue #168 / PR #169) [h/t @frascuchon]
- Add `six` as explicit dependency (for now)

## [0.5.15] — 2020-01-05
### Changed
- Upgrade `pdfminer.six` requirement to `==20200104`
- Upgrade `pillow` requirement `>=7.0.0`
- Remove Python 2.7 and 3.4 from `tox` tests

## [0.5.14] — 2019-10-06
### Fixed
- Fix sorting bug in `page.extract_table()`
- Fix support for password-protected PDFs (PR #138)

## [0.5.13] — 2019-08-29
### Fixed
- Fixed PDF object resolution for rotation (PR #136)

## [0.5.12] — 2019-04-14
### Added
- `cdecimal` support for Python 2
- Support for password-protected PDFs

## [0.5.11] — 2018-11-13
### Added
- Caching for `.decimalize()` method

### Changed
- Upgrade to `pdfminer.six==20181108`
- Make whitespace checking more robust (PR #88)

### Fixed
- Fix issue #75 (`.to_image()` custom arguments)
- Fix issue raised in PR #77 (PDFObjRef resolution), and general class of problems
- Fix issue #90, and general class of problems, by explicitly typecasting each kind of PDF Object

## [0.5.10] — 2018-08-03
### Fixed
- Fix bug in which, when calling get_page_image(...), the alpha channel could make the whole page black out.

## [0.5.9] — 2018-07-10
### Fixed
- Fix issue #67, in which bool-type metadata were handled incorrectly

## [0.5.8] — 2018-03-06
### Fixed
- Fix issue #53, in which non-decimalize-able (non_)stroking_color properties were raising errors.

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
