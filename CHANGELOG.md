# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](http://keepachangelog.com/).

## [0.8.0] - 2023-02-13

### Changed

- Change the (still experimental) `Page/utils.extract_text(layout=True)` approach so that it pads, to the degree necessary, the ends of lines with spaces and the end of the text with blank lines to acheive better mimicry of page layout. ([d3662de](https://github.com/jsvine/pdfplumber/commit/d3662de))
- Refactor handling of `pts` attribute and, in doing so, deprecate the `curve_obj["points"]` attribute, and fix `PageImage.draw_line(...)`'s handling of diagonal lines. ([216bedd](https://github.com/jsvine/pdfplumber/commit/216bedd))
- Breaking change: In `Page.extract_table[s](...)`, `keep_blank_chars` must now be passed as `text_keep_blank_chars`, for consistency's sake. ([c4e1b29](https://github.com/jsvine/pdfplumber/commit/c4e1b29))

### Added

- Add `Page.extract_table[s](...)` support for all `Page.extract_text(...)` keyword arguments. ([c4e1b29](https://github.com/jsvine/pdfplumber/commit/c4e1b29))
- Add `height` and `width` keyword arguemnts to `Page.to_image(...)`. ([#798](https://github.com/jsvine/pdfplumber/issues/798) + [93f7dbd](https://github.com/jsvine/pdfplumber/commit/93f7dbd))
- Add `layout_width`, `layout_width_chars`, `layout_height`, and `layout_width_chars` parameters to `Page/utils.extract_text(layout=True)`. ([d3662de](https://github.com/jsvine/pdfplumber/commit/d3662de))
- Add CITATION.cff. ([#755](https://github.com/jsvine/pdfplumber/issues/755)) [h/t @joaoccruz]

### Fixed

- Fix simple edge-case for when page rotation is (incorrectly) set to `None`. ([#811](https://github.com/jsvine/pdfplumber/pull/811)) [h/t @toshi1127]

### Development Changes

- Convert `utils.py` into `utils/` submodules. Retains same interface, just an improvement in organization. ([6351d97](https://github.com/jsvine/pdfplumber/commit/6351d97))
- Fix typing hints to include io.BytesIO. ([d4107f6](https://github.com/jsvine/pdfplumber/commit/d4107f6)) [h/t @conitrade-as]
- Refactor text-extraction utilities, paving way for better consistency across various entrypoints to text extraction (e.g., via `utils.extract_text(...)`, via `Page.extract_text(...)`, via `Page.extract_table(...)`). ([3424b57](https://github.com/jsvine/pdfplumber/commit/3424b57))

## [0.7.6] - 2022-11-22

### Changed

- Bump pinned `pdfminer.six` version to `20221105`. ([e63a038](https://github.com/jsvine/pdfplumber/commit/e63a038))

### Fixed

- Restore `text` attribute to `.textboxhorizontal`/etc., regression introduced in `9587cc7` / `v0.6.2`. ([8a0c126](https://github.com/jsvine/pdfplumber/commit/8a0c126))
- Fix `lru_cache` usage, which are [discouraged for class methods](https://rednafi.github.io/reflections/dont-wrap-instance-methods-with-functoolslru_cache-decorator-in-python.html) due to garbage-collection issues. ([e3142a0](https://github.com/jsvine/pdfplumber/commit/e3142a0))

### Development Changes

- Upgrade `nbexec` development requirement from `0.1.0` to `0.2.0`. ([30dac25](https://github.com/jsvine/pdfplumber/commit/30dac25))

## [0.7.5] - 2022-10-01

### Added

- Add `PageImage.show()` as alias for `PageImage.annotated.show()`. ([#715](https://github.com/jsvine/pdfplumber/discussions/715) + [5c7787b](https://github.com/jsvine/pdfplumber/commit/5c7787b))

### Fixed

- Fixed issue where `py.typed` file was not included in PyPi distribution. ([#698](https://github.com/jsvine/pdfplumber/issues/698) + [#703](https://github.com/jsvine/pdfplumber/pull/703) + [6908487](https://github.com/jsvine/pdfplumber/commit/6908487)) [h/t @jhonatan-lopes]
- Reinstated the ability to call `utils.cluster_objects(...)` with any hashable value (`str`, `int`, `tuple`, etc.) as the `key_fn` parameter, reverting breaking change in [58b1ab1](https://github.com/jsvine/pdfplumber/commit/58b1ab1). ([#691](https://github.com/jsvine/pdfplumber/issues/691) + [1e97656](https://github.com/jsvine/pdfplumber/commit/1e97656)) [h/t @jfuruness]

### Development Changes

- Update Wand version in `requirements.txt` from `>=0.6.7` to `>=0.6.10`. ([#713](https://github.com/jsvine/pdfplumber/issues/713) + [3457d79](https://github.com/jsvine/pdfplumber/commit/3457d79))

## [0.7.4] - 2022-07-19

### Added

- Add `utils.outside_bbox(...)` and `Page.outside_bbox(...)` method, which are the inverse of `utils.within_bbox(...)` and `Page.within_bbox(...)`. ([#369](https://github.com/jsvine/pdfplumber/issues/369) + [3ab1cc4](https://github.com/jsvine/pdfplumber/commit/3ab1cc4))
- Add `strict=True/False` parameter to `Page.crop(...)`, `Page.within_bbox(...)`, and `Page.outside_bbox(...)`; default is `True`, while `False` bypasses the `test_proposed_bbox(...)` check. ([#421](https://github.com/jsvine/pdfplumber/issues/421) + [71ad60f](https://github.com/jsvine/pdfplumber/commit/71ad60f))
- Add more guidance to exception when `.to_image(...)` raises `PIL.Image.DecompressionBombError`. ([#413](https://github.com/jsvine/pdfplumber/issues/413) + [b6ff9e8](https://github.com/jsvine/pdfplumber/commit/b6ff9e8))

### Fixed

- Fix `PageImage` conversions for PDFs with `cmyk` colorspaces; convert them to `rgb` earlier in the process. ([28330da](https://github.com/jsvine/pdfplumber/commit/28330da))

## [0.7.3] - 2022-07-18

### Fixed

- Quick fix for transparency issue in visual debugging mode. ([b98dd7c](https://github.com/jsvine/pdfplumber/commit/b98dd7c))

## [0.7.2] - 2022-07-17

### Added

- Add `split_at_punctuation` parameter to `.extract_words(...)` and `.extract_text(...)`. ([#682](https://github.com/jsvine/pdfplumber/issues/674)) [h/t @lolipopshock]
- Add README.md link to @hbh112233abc's [Chinese translation of README.md](https://github.com/hbh112233abc/pdfplumber/blob/stable/README-CN.md). ([#674](https://github.com/jsvine/pdfplumber/issues/674))

### Changed

- Change `.to_image(...)`'s approach, preferring to composite with a white background instead of removing the alpha channel. ([1cd1f9a](https://github.com/jsvine/pdfplumber/commit/1cd1f9a))

### Fixed

- Fix bug in `LayoutEngine.calculate(...)` when processing char objects with len>1 representations, such as ligatures. ([#683](https://github.com/jsvine/pdfplumber/issues/683))

## [0.7.1] - 2022-05-31

### Fixed

- Fix bug when calling `PageImage.debug_tablefinder()` (i.e., with no parameters). ([#659](https://github.com/jsvine/pdfplumber/issues/659) + [063e2ed](https://github.com/jsvine/pdfplumber/commit/063e2ed)) [h/t @rneumann7]

### Development Changes

- Add `Makefile` target for `examples`, as well as dev requirements to support re-running the example notebooks automatically. ([ef065a7](https://github.com/jsvine/pdfplumber/commit/ef065a7))

## [0.7.0] - 2022-05-27

### Added

- Add `"matrix"` property to `char` objects, representing the current transformation matrix. ([ae6f99e](https://github.com/jsvine/pdfplumber/commit/ae6f99e))
- Add `pdfplumber.ctm` submodule with class `CTM`, to calculate scale, skew, and translation of a current transformation matrix obtained from a `char`'s `"matrix"` property. ([ae6f99e](https://github.com/jsvine/pdfplumber/commit/ae6f99e))
- Add `page.search(...)`, an *experimental feature* that allows you to search a page's text via regular expressions and non-regex strings, returning the text, any regex matches, the bounding box coordinates, and the char objects themselves. ([#201](https://github.com/jsvine/pdfplumber/issues/201) + [58b1ab1](https://github.com/jsvine/pdfplumber/commit/58b1ab1))
- Add `--include-attrs`/`--exclude-attrs` to CLI (and corresponding params to `.to_json(...)`, `.to_csv(...)`, and `Serializer`. ([4deac25](https://github.com/jsvine/pdfplumber/commit/4deac25))
- Add `py.typed` for PEP561 compatibility and detection of typing hints by mypy. ([ca795d1](https://github.com/jsvine/pdfplumber/commit/ca795d1)) [h/t @jhonatan-lopes]

### Changed

- Bump pinned `pdfminer.six` version to `20220524`. ([486cea8](https://github.com/jsvine/pdfplumber/commit/486cea8))

### Removed

- Remove `utils.collate_chars(...)`, the old name (and then alias) for `utils.extract_text(...)`. ([24f3532](https://github.com/jsvine/pdfplumber/commit/24f3532))
- Remove `utils._itemgetter(...)`, an internal-use method previously used by `utils.cluster_objects(...)`. ([58b1ab1](https://github.com/jsvine/pdfplumber/commit/58b1ab1))

### Fixed

- Fix `IndexError` bug for `.extract_text(layout=True)` on pages without text. ([#658](https://github.com/jsvine/pdfplumber/issues/658) + [ad3df11](https://github.com/jsvine/pdfplumber/commit/ad3df11)) [h/t @ethanscorey]

## [0.6.2] - 2022-05-06

### Added

- Add type annotations, and refactor parts of the library accordingly. ([9587cc7](https://github.com/jsvine/pdfplumber/commit/9587cc7d2292a1eae7a0150ab406f9365944266f))
- Add enforcement of type annotations via `mypy --strict`. ([cdfdb87](https://github.com/jsvine/pdfplumber/commit/cdfdb87a215fed6cdc0db3a218c35bf18d399cbe))
- Add final bits of test coverage. ([feb9d08](https://github.com/jsvine/pdfplumber/commit/feb9d082d7afb31edd0838cb93666d1e71c119da))
- Add `TableSettings` class, a behind-the-scenes handler for managing and validating table-extraction settings. ([9587cc7](https://github.com/jsvine/pdfplumber/commit/9587cc7d2292a1eae7a0150ab406f9365944266f))

### Changed

- Rename the positional argument to `.to_csv(...)` and `.to_json(...)` from `types` to `object_types`. ([9587cc7](https://github.com/jsvine/pdfplumber/commit/9587cc7d2292a1eae7a0150ab406f9365944266f))
- Tweak the output of `.to_json(...)` so that, if an object type is not present for a given page, it has no key in the page's object representation. ([9587cc7](https://github.com/jsvine/pdfplumber/commit/9587cc7d2292a1eae7a0150ab406f9365944266f))

### Removed

- Remove `utils.filter_objects(...)` and move the functionality to within the `FilteredPage.objects` property calculation, the only part of the library that used it. ([9587cc7](https://github.com/jsvine/pdfplumber/commit/9587cc7d2292a1eae7a0150ab406f9365944266f))
- Remove code that sets `pdfminer.pdftypes.STRICT = True` and `pdfminer.pdfinterp.STRICT = True`, since that [has now been the default for a while](https://github.com/pdfminer/pdfminer.six/commit/9439a3a31a347836aad1c1226168156125d9505f). ([9587cc7](https://github.com/jsvine/pdfplumber/commit/9587cc7d2292a1eae7a0150ab406f9365944266f))

## [0.6.1] - 2022-04-23

### Changed
- Bump pinned `pdfminer.six` version to `20220319`. ([e434ed0](https://github.com/jsvine/pdfplumber/commit/e434ed0b196f1f2c0b7f76e8ea2663e40c99e93c))
- Bump minimum `Pillow` version to `>=9.1`. ([d88eff1](https://github.com/jsvine/pdfplumber/commit/d88eff1e5354baa219ebff244fd4ab0e74db49c5))
- Drop support for Python 3.6 (EOL Dec. 2021) ([a32473e](https://github.com/jsvine/pdfplumber/commit/a32473ee5f9113d5c5a96b30270cafc58d170f46))

### Fixed
- If `pdfplumber.open(...)` opens a file but a `pdfminer.pdfparser.PSException` is raised during the process, `pdfplumber` now makes sure to close that file. ([#581](https://github.com/jsvine/pdfplumber/pull/581) + ([#578](https://github.com/jsvine/pdfplumber/issues/578)) [h/t @johnhuge]
- Fix incompatibility with `Pillow>=9.1`. ([#637](https://github.com/jsvine/pdfplumber/issues/637))

## [0.6.0] - 2021-12-21
### Added
- Add `.extract_text(layout=True)`, an *experimental feature* which attempts to mimic the structural layout of the text on the page. ([#10](https://github.com/jsvine/pdfplumber/issues/10))
- Add `utils.merge_bboxes(bboxes)`, which returns the smallest bounding box that contains all bounding boxes in the `bboxes` argument. ([f8d5e70](https://github.com/jsvine/pdfplumber/commit/f8d5e70a509aa9ed3ee565d7d3f97bb5ec67f5a5))
- Add `--precision` argument to CLI ([#520](https://github.com/jsvine/pdfplumber/pull/520))
- Add `snap_x_tolerance` and `snap_y_tolerance` to table extraction settings. ([#51](https://github.com/jsvine/pdfplumber/pull/51) + [#475](https://github.com/jsvine/pdfplumber/issues/475)) [h/t @dustindall]
- Add `join_x_tolerance` and `join_y_tolerance` to table extraction settings. ([cbb34ce](https://github.com/jsvine/pdfplumber/commit/cbb34ce28b9b66d8d709304bbd0de267d82d75f3))

### Changed
- Upgrade `pdfminer.six` from `20200517` to `20211012`; see [that library's changelog](https://github.com/pdfminer/pdfminer.six/blob/develop/CHANGELOG.md) for details, but a key difference is an improvement in how it assigns `line`, `rect`, and `curve` objects. (Diagonal two-point lines, for instance, are now `line` objects instead of `curve` objects.) ([#515](https://github.com/jsvine/pdfplumber/pull/515))
- Remove Decimal-ization of parsed object attributes, which are now represented with as much precision as is returned by `pdfminer.six` ([#346](https://github.com/jsvine/pdfplumber/discussions/346) + [#520](https://github.com/jsvine/pdfplumber/pull/520))
- `.extract_text(...)` returns `""` instead of `None` when character list is empty. ([#482](https://github.com/jsvine/pdfplumber/issues/482) + [cb9900b](https://github.com/jsvine/pdfplumber/commit/cb9900b49706e96df520dbd1067c2a57a4cdb20d)) [h/t @tungph]
- `.extract_words(...)` now includes `doctop` among the attributes it returns for each word. ([66fef89](https://github.com/jsvine/pdfplumber/commit/66fef89b670cf95d13a5e23040c7bf9339944c01))
- Change behavior of horizontal `text_strategy`, so that it uses the top and bottom of *every* word, not just the top of every word and the bottom of the last. ([#467](https://github.com/jsvine/pdfplumber/pull/467) + [#466](https://github.com/jsvine/pdfplumber/issues/466) + [#265](https://github.com/jsvine/pdfplumber/issues/265)) [h/t @bobluda + @samkit-jain]
- Change `table.merge_edges(...)` behavior when `join_tolerance` (and `x`/`y` variants) `<= 0`, so that joining is attempted regardless, to handle cases of overlapping lines. ([cbb34ce](https://github.com/jsvine/pdfplumber/commit/cbb34ce28b9b66d8d709304bbd0de267d82d75f3))
- Raise error if certain table-extraction settings are negative. ([aa2d594](https://github.com/jsvine/pdfplumber/commit/aa2d594d3b3352dbcef503e4df2e045d69fc2511))

### Fixed
- Fix slowdown in `.extract_words(...)`/`WordExtractor.iter_chars_to_words(...)` on very long words, caused by repeatedly re-calculating bounding box. ([#483](https://github.com/jsvine/pdfplumber/discussions/483))
- Handle `UnicodeDecodeError` when trying to decode utf-16-encoded annotations ([#463](https://github.com/jsvine/pdfplumber/issues/463)) [h/t @tungph]
- Fix crash when extracting tables with null values in `(text|intersection)_(x|y)_tolerance` settings. ([#539](https://github.com/jsvine/pdfplumber/discussions/539)) [h/t @yoavxyoav]

### Removed
- Remove `pdfplumber.load(...)` method, which has been deprecated since `0.5.23` ([54cbbc5](https://github.com/jsvine/pdfplumber/commit/54cbbc5321b42f3976b2ac750c25b7b2ec6045d7))

### Development Changes
- Add `CONTRIBUTING.md` ([#428](https://github.com/jsvine/pdfplumber/pull/428))
- Enforce import order via [`isort`](https://pycqa.github.io/isort/index.html) ([d72b879](https://github.com/jsvine/pdfplumber/commit/d72b879665b410bd0f9c436d54ae60b3989489d5))
- Update Pillow and Wand versions in `requirements.txt` ([cae6924](https://github.com/jsvine/pdfplumber/commit/cae69246c53e49f95c1adbb5dffb3d49e726c5df))
- Update all dependency versions in `requirements-dev.txt` ([2f7e7ee](https://github.com/jsvine/pdfplumber/commit/2f7e7ee49172d681f34269a0db0276dffefa6386))

## [0.5.28] — 2021-05-08
### Added
- Add `--laparams` flag to CLI. ([#407](https://github.com/jsvine/pdfplumber/pull/407))

### Changed
- Change `.convert_csv(...)` to order objects first by page number, rather than object type. ([#407](https://github.com/jsvine/pdfplumber/pull/407))
- Change `.convert_csv(...)`, `.convert_json(...)`, and CLI so that, by default, they returning all available object types, rather than those in a predefined default list. ([#407](https://github.com/jsvine/pdfplumber/pull/407))

### Fixed
- Fix `.extract_text(...)` so that it can accept generator objects as its main parameter. ([#385](https://github.com/jsvine/pdfplumber/pull/385)) [h/t @alexreg]
- Fix page-parsing so that `LTAnno` objects (which have no bounding-box coordinates) are not extracted. (Was only an issue when setting `laparams`.) ([#388](https://github.com/jsvine/pdfplumber/issues/383))
- Fix `Page.extract_table(...)` so that it honors text tolerance settings ([#415](https://github.com/jsvine/pdfplumber/issues/415)) [h/t @trifling]

## [0.5.27] — 2021-02-28
### Fixed
- Fix regression (introduced in `0.5.26`/[b1849f4](https://github.com/jsvine/pdfplumber/commit/b1849f4)) in closing files opened by `PDF.open`
- Reinstate access to higher-level layout objects (such as `textboxhorizontal`) when `laparams` is passed to `pdfplumber.open(...)`. Had been removed in `0.5.24` via [1f87898](https://github.com/jsvine/pdfplumber/commit/1f878988576017b64f5cd77e1eb21b401124c699). ([#359](https://github.com/jsvine/pdfplumber/issues/359) + [#364](https://github.com/jsvine/pdfplumber/pull/364))

### Development Changes
- Add a `python setup.py build sdist` test to main GitHub action. ([#365](https://github.com/jsvine/pdfplumber/pull/365))

## [0.5.26] — 2021-02-10
### Added
- Add `Page.close/__enter__/__exit__` methods, by generalizing that behavior through the `Container` class ([b1849f4](https://github.com/jsvine/pdfplumber/commit/b1849f4))

### Changed
- Change handling of floating point numbers; no longer convert them to `Decimal` objects and do not round them
- Change `TableFinder` to return tables in order of topmost-and-then-leftmost, rather than leftmost-and-then-topmost ([#336](https://github.com/jsvine/pdfplumber/issues/336))
- Change `Page.to_image()`'s handling of alpha layer, to remove aliasing artifacts ([#340](https://github.com/jsvine/pdfplumber/pull/340)) [h/t @arlyon]

### Development Changes

- Enforce `psf/black` and `flake8` on `tests/` ([#327](https://github.com/jsvine/pdfplumber/pull/327)

## [0.5.25] — 2020-12-09
### Added
- Add new boolean argument `strict_metadata` (default `False`) to `pdfplumber.open(...)` method for handling metadata resolution failures ([f2c510d](https://github.com/jsvine/pdfplumber/commit/f2c510d))

### Fixed
- Fix metadata extraction to handle integer/floating-point values ([cb32478](https://github.com/jsvine/pdfplumber/commit/cb32478)) ([#297](https://github.com/jsvine/pdfplumber/issues/297))
- Fix metadata extraction to handle nested metadata values ([2d9415](https://github.com/jsvine/pdfplumber/commit/2d9415)) ([#316](https://github.com/jsvine/pdfplumber/issues/316))
- Explicitly load text as utf-8 in `setup.py` ([7854328](https://github.com/jsvine/pdfplumber/commit/7854328)) ([#304](https://github.com/jsvine/pdfplumber/issues/304))
- Fix `pdfplumber.open(...)` so that it does not close file objects passed to it ([408605f](https://github.com/jsvine/pdfplumber/commit/408605f)) ([#312](https://github.com/jsvine/pdfplumber/issues/312))


## [0.5.24] — 2020-10-20
### Added
- Added `extra_attrs=[...]` parameter to `.extract_text(...)` ([c8b200e](https://github.com/jsvine/pdfplumber/commit/c8b200e)) ([#28](https://github.com/jsvine/pdfplumber/issues/28))
- Added `utils/page.dedupe_chars(...)` ([04fd56a](https://github.com/jsvine/pdfplumber/commit/04fd56a) + [b132d45](https://github.com/jsvine/pdfplumber/commit/b132d45)) ([#71](https://github.com/jsvine/pdfplumber/issues/71))

### Changed
- Change character attribute `upright` from `int` to `bool` (per original `pdfminer.six` representation) ([1f87898](https://github.com/jsvine/pdfplumber/commit/1f87898))
- Remove access and reference to `Container.figures`, given that they are not fundamental objects ([8e74cb9](https://github.com/jsvine/pdfplumber/commit/8e74cb9))

### Fixed
- Decimalize "simple" `explicit_horizontal_lines`/`explicit_vertical_lines` descs passed to `TableFinder` methods ([bc40779](https://github.com/jsvine/pdfplumber/commit/bc40779)) ([#290](https://github.com/jsvine/pdfplumber/issues/290))

### Development Changes

- Refactor/simplify `Page.process_objects` ([1f87898](https://github.com/jsvine/pdfplumber/commit/1f87898)), `utils.extract_words` ([c8b200e](https://github.com/jsvine/pdfplumber/commit/c8b200e)), and `convert.serialize` ([a74d3bc](https://github.com/jsvine/pdfplumber/commit/a74d3bc))
- Remove `test_issues.py:test_pr_77` ([917467a](https://github.com/jsvine/pdfplumber/commit/917467a)) and narrow `test_ca_warn_report:test_objects` ([6233bbd](https://github.com/jsvine/pdfplumber/commit/6233bbd)) to speed up tests

## [0.5.23] — 2020-08-15
### Added
- Add `utils.resolve` (non-recursive .resolve_all) ([7a90630](https://github.com/jsvine/pdfplumber/commit/7a90630))
- Add `page.annots` and `page.hyperlinks`, replacing non-functional `page.annos`, and mirroring pdfminer's language ("annot" vs. "anno"). ([aa03961](https://github.com/jsvine/pdfplumber/commit/aa03961))
- Add `page/pdf.to_json` and `page/pdf.to_csv` ([cbc91c6](https://github.com/jsvine/pdfplumber/commit/cbc91c6))
- Add `relative=True/False` parameter to `.crop` and `.within_bbox`; those methods also now raise exceptions for invalid and out-of-page bounding boxes. ([047ad34](https://github.com/jsvine/pdfplumber/commit/047ad34)) [h/t @samkit-jain]

### Changed
- Remove `pdfminer.from_path` and `pdfminer.load` as deprecated; now `pdfminer.open` is the canonical way to load a PDF. ([00e789b](https://github.com/jsvine/pdfplumber/commit/00e789b))
- Simplify the logic in "text" table-finding strategies; in edge cases, may result in changes to results. ([d224202](https://github.com/jsvine/pdfplumber/commit/d224202))
- Drop support for Python 3.5 ([baf1033](https://github.com/jsvine/pdfplumber/commit/baf1033))

### Fixed
- Fix `.extract_words`, which had been returning incorrect results when `horizontal_ltr = False` ([d16aa13](https://github.com/jsvine/pdfplumber/commit/d16aa13))
- Fix `utils.resize_object`, which had been failing in various permutations ([d16aa13](https://github.com/jsvine/pdfplumber/commit/d16aa13))
- Fix `lines_strict` table-finding strategy, which a typo had prevented from being usable ([f0c9b85](https://github.com/jsvine/pdfplumber/commit/f0c9b85))
- Fix `utils.resolve_all` to guard against two known sources of infinite recursion ([cbc91c6](https://github.com/jsvine/pdfplumber/commit/cbc91c6))

### Development Changes

- Rename default branch to "stable," to clarify its purpose
- Reformat code with psf/black ([1258e09](https://github.com/jsvine/pdfplumber/commit/1258e09))
- Add code linting via psf/black and flake8 ([1258e09](https://github.com/jsvine/pdfplumber/commit/1258e09))
- Switch from nosetests to pytest ([1ac16dd](https://github.com/jsvine/pdfplumber/commit/1ac16dd))
- Switch from pipenv to standard requirements.txt + python -m venv ([48eaa51](https://github.com/jsvine/pdfplumber/commit/48eaa51))
- Add GitHub action for tests + codecov ([b148fd1](https://github.com/jsvine/pdfplumber/commit/b148fd1))
- Add Makefile for building development virtual environment and running tests ([4c69c58](https://github.com/jsvine/pdfplumber/commit/4c69c58))
- Add badges to README.md ([9e42dc3](https://github.com/jsvine/pdfplumber/commit/9e42dc3))
- Add Trove classifiers for Python versions to setup.py ([6946e8d](https://github.com/jsvine/pdfplumber/commit/6946e8d))
- Add MANIFEST.in ([eafc15c](https://github.com/jsvine/pdfplumber/commit/eafc15c))
- Add GitHub issue templates ([c4156d6](https://github.com/jsvine/pdfplumber/commit/c4156d6))
- Remove `pandas` from dev requirements and tests ([a5e7d7f](https://github.com/jsvine/pdfplumber/commit/a5e7d7f))

## [0.5.22] — 2020-07-18
### Changed
- Upgraded `pdfminer.six` requirement to `==20200517` ([cddbff7](https://github.com/jsvine/pdfplumber/commit/cddbff7)) [h/t @youngquan]

### Added
- Add support for `non_stroking_color` attribute on `char` objects ([0254da3](https://github.com/jsvine/pdfplumber/commit/0254da3)) [h/t @idan-david]

## [0.5.21] — 2020-05-27
### Fixed
- Fix `Page.extract_table(...)` to return `None` instead of crashing when no table is found ([d64afa8](https://github.com/jsvine/pdfplumber/commit/d64afa8)) [h/t @stucka]

## [0.5.20] — 2020-04-29
### Fixed
- Fix `.get_page_image` to prefer paths over streams, when possible ([ab957de](https://github.com/jsvine/pdfplumber/commit/ab957de)) [h/t @ubmarco]
- Local-fix pdfminer.six's `.resolve_all` to handle tuples and simplify ([85f422d](https://github.com/jsvine/pdfplumber/commit/85f422d))

### Changed
- Remove support for Python 2 and Python <3.3

## [0.5.19] — 2020-04-16
### Changed
- Add `utils.decimalize` performance improvement ([830d117](https://github.com/jsvine/pdfplumber/commit/830d117)) [h/t @ubmarco]

### Fixed
- Fix un-referenced method when using "text" table-finding strategy ([2a0c4a2](https://github.com/jsvine/pdfplumber/commit/2a0c4a2))
- Add missing object type `rect_edge` to `obj_to_edges()` ([0edc6bf](https://github.com/jsvine/pdfplumber/commit/0edc6bf))

## [0.5.18] — 2020-04-01
### Changed
- Allow `rect` and `curve` objects also to be passed to "explicit_..._lines" setting when table-finding. (And disallow other types of dicts to be passed.)

### Fixed
- Fix `utils.extract_text` bug introduced in prior version

## [0.5.17] — 2020-04-01
### Fixed
- Fix and simplify obj-in-bbox logic (see commit [25672961](https://github.com/jsvine/pdfplumber/commit/25672961))
- Improve/fix the way `utils.extract_text` handles vertical text (see commit [8a5d858b](https://github.com/jsvine/pdfplumber/commit/8a5d858b)) [h/t @dwalton76]
- Have `Page.to_image` use bytes stream instead of file path (Issue [#124](https://github.com/jsvine/pdfplumber/issues/124) / PR [#179](https://github.com/jsvine/pdfplumber/pull/179)) [h/t @cheungpat]
- Fix issue [#176](https://github.com/jsvine/pdfplumber/issues/176), in which `Page.extract_tables` did not pass kwargs to `Table.extract` [h/t @jsfenfen]

## [0.5.16] — 2020-01-12
### Fixed
- Prevent custom LAParams from raising exception (Issue [#168](https://github.com/jsvine/pdfplumber/issues/168) / PR [#169](https://github.com/jsvine/pdfplumber/pull/169)) [h/t @frascuchon]
- Add `six` as explicit dependency (for now)

## [0.5.15] — 2020-01-05
### Changed
- Upgrade `pdfminer.six` requirement to `==20200104`
- Upgrade `pillow` requirement `>=7.0.0`
- Remove Python 2.7 and 3.4 from `tox` tests

## [0.5.14] — 2019-10-06
### Fixed
- Fix sorting bug in `page.extract_table()`
- Fix support for password-protected PDFs (PR [#138](https://github.com/jsvine/pdfplumber/pull/138))

## [0.5.13] — 2019-08-29
### Fixed
- Fixed PDF object resolution for rotation (PR [#136](https://github.com/jsvine/pdfplumber/pull/136))

## [0.5.12] — 2019-04-14
### Added
- `cdecimal` support for Python 2
- Support for password-protected PDFs

## [0.5.11] — 2018-11-13
### Added
- Caching for `.decimalize()` method

### Changed
- Upgrade to `pdfminer.six==20181108`
- Make whitespace checking more robust (PR [#88](https://github.com/jsvine/pdfplumber/pull/88))

### Fixed
- Fix issue [#75](https://github.com/jsvine/pdfplumber/issues/75) (`.to_image()` custom arguments)
- Fix issue raised in PR [#77](https://github.com/jsvine/pdfplumber/pull/77) (PDFObjRef resolution), and general class of problems
- Fix issue [#90](https://github.com/jsvine/pdfplumber/issues/90), and general class of problems, by explicitly typecasting each kind of PDF Object

## [0.5.10] — 2018-08-03
### Fixed
- Fix bug in which, when calling get_page_image(...), the alpha channel could make the whole page black out.

## [0.5.9] — 2018-07-10
### Fixed
- Fix issue [#67](https://github.com/jsvine/pdfplumber/issues/67), in which bool-type metadata were handled incorrectly

## [0.5.8] — 2018-03-06
### Fixed
- Fix issue [#53](https://github.com/jsvine/pdfplumber/issues/53), in which non-decimalize-able (non_)stroking_color properties were raising errors.

## [0.5.7] — 2018-01-20
### Added
- `.travis.yml`, but failing on `.to_image()`

### Changed
- Move from defunct `pycrypto` to `pycryptodome`
- Update `pdfminer.six` to `20170720`

## [0.5.6] — 2017-11-21
### Fixed
- Fix issue [#41](https://github.com/jsvine/pdfplumber/issues/41), in which PDF-object-referenced cropboxes/mediaboxes weren't being fully resolved.

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

