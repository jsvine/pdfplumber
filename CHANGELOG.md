# Change Log

All notable changes to this project will be documented in this file. Currently goes back to `v0.4.3`.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

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
