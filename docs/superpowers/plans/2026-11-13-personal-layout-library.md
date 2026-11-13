# Personal layout library Implementation Plan — revised

> Implement with subagents on separate file ownership; root integrates and reviews. Use TDD and record evidence. User authorized implementation, fork, and subagents on 2026-11-13.

**Goal:** One Windows .exe with a visual receipt editor, thumbnail library, portable editable layouts, and AB-88H network printing including intermediate cuts.
**Architecture:** Keep upstream Python/PySide6. Library is local files outside the executable. Shared document rendering prepares identical preview and print pixels. Cuts are metadata, not ink.
**Spec:** This document and the original detailed handoff at ../../../.. (project chat outputs). Upstream base bd671b0ed0c663f485d2c16876d9ab7e14dc6c84. Existing code is not yet runtime-verified; public interfaces below may be adjusted after baseline with an explicit recorded ruling.

## Global Constraints
- 80mm paper, 72mm printable centered area, 576px bitmap, 203 nominal DPI / 8 dots/mm reference. Preserve 4mm unprintable paper margins instead of shrinking an entire 80mm drawing into 72mm.
- AB-88H at configurable 192.168.1.10:9100. Normal routing first; prefer printer on router LAN. Explicit local IP/interface optional advanced fallback only. Never alter OS IPs/routes automatically. The previously used local .20 is transient, index 10 is machine-specific.
- Hardware Dark/Slow already enabled by user DIP6/7 ON. Software darkness is a bitmap threshold, not physical DIP control.
- User approved daily/cinema reinforced v2 PNGs in parent chat outputs. Rebuild native editable text/shapes, not full-page PNG imports. Thin functional lines >=2 final pixels.
- Main window library and editor; no automatic printing, no automatic resend following ambiguous transmission. Report sent vs physical success honestly.
- Keep old JSONs readable. schema_version distinct from document version. New letter_spacing_px float=0 renders positive and negative spacing and is persisted/cache-aware.
- V1: library search/open/create/save/duplicate/rename/trash/restore; atomic saves and portable assets. Defer previous revision history, extra CI workflow, formal 150% DPI QA, arbitrary element/pixel caps, online content APIs, RPi/mobile/cloud.
- Cinema old reference omitted four printed perforation rows; new native cut metadata adds no ink, so split without dropping image rows.
- No new approval for already authorized fork. A new sharing/publishing action remains separate from local implementation.

## Shared contracts and ownership
Library agent owns receipt_designer/library.py and tests/test_library.py only. LibraryRepository(root: Path): list_layouts(query=''), load(id)->Template, save(template, *, layout_id=None, preview=None)->LayoutInfo, duplicate(id,new_name), rename(id,new_name), trash(id), restore(id); LayoutInfo.id/name/folder/thumbnail/updated_at. save preview accepts PIL.Image or None. Assets become internal relative files; loaded image paths absolute; documents include metadata.json/document.json/preview.png/assets, .trash recoverable. No Qt dependency.

Printing agent owns core/models.py; printing/jobs.py, escpos_raster.py, backends.py, worker.py; ui/print_render.py; related tests. ThermalProfile.from_config(dict) with width_px=576, printable_width_mm=72, paper_width_mm=80, threshold=170, conversion='threshold', cut_mode='full', feed_lines=4. CutMarker(position_mm, mode='full'). Template.cut_markers=[] and schema_version=2; Element.letter_spacing_px=0. prepare_print_job(template, profile)->PreparedPrintJob(preview PIL.Image, parts list[PrintPart(image PIL.Image, cut_after)]). pil_to_qimage(PIL.Image)->QImage in ui/print_render.py. PrinterWorker accepts payload['job'] plus config, keeps legacy image payload. Print result signals preserve error handling, no false success on failed/uncertain transmission.

UI agent owns ui/library_page.py; main_window_impl.py, actions.py, persistence.py, host_protocols.py; dialogs/cut_markers.py and printer_config.py/print_preview.py if needed; tests/test_library_ui.py. Editor takes a snapshot from scene elements before library save/printing. Call printing contracts above, do not edit their owned files. Navigation guards unsaved document. Library settings allow root choice; root override RECEIPT_DESIGNER_LIBRARY for test/portable evaluation.

Root owns ui/items.py and ui/properties.py typography paint/cache/property control, personal templates and tests, packaging/docs/baseline. Coordinate with printing agent's model addition.

### Task 1: Runtime baseline and fork
- [ ] Create fork joaopef/receipt-designer; isolated fresh clone and feat/personal-layout-library branch.
- [ ] Install venv, run upstream tests with RUN_QT_TESTS=1 QT_QPA_PLATFORM=offscreen, record failures and fix blockers with regression tests.
- [ ] Lock validated dependencies, read repository instructions, record adjusted interfaces after runtime inspection.

### Task 2: Library first usable feature
- [ ] Write failing tests covering roundtrip, portable/missing assets, duplicate independence, search unicode, atomic failure, trash/restore.
- [ ] Implement minimal repository and library UI alongside existing editor.
- [ ] UI tests cover save/open/new/rename/duplicate/search and unsaved save/discard/cancel. Run existing suite.

### Task 3: Compatible documents, typography, common raster preparation
- [ ] Tests RED: old JSON, cuts roundtrip/invalid/colliding, letter spacing positive/negative; rendering hides guide/selection; output width576, cuts retain all rows.
- [ ] Implement models and render preparation, font-spacing rendering and cache invalidation, property control.
- [ ] Tests GREEN plus existing suite. Reuse current drawing primitives; no duplicate editor renderer.

### Task 4: Network jobs and early physical integration
- [ ] RED/GREEN byte decoding tests of GS v 0 row widths/polarity and per-part cut ordering; real local TCP server tests, interruption gives uncertain and no resend.
- [ ] Stream bands <=48 rows, preserve validated ESC d4 + GS V0 cut; backend optional Windows source/interface (not default).
- [ ] Add cut positions dialog and prepare-once preview/print UI. Ensure no guide/cut marker ink.
- [ ] Early physical short text/2px line/intermediate-cut test when printer ready and user explicitly authorizes; independent UI/build work continues if unavailable. No silent physical tests.

### Task 5: Editable personal models
- [ ] Build native JSON daily/cinema based on approved v2 sources; Courier New/Arial Black and explicit letter_spacing_px.
- [ ] Tests verify editable title/tasks/film, 64 chess squares and valid board, cinema intermediate cut, packaged asset paths.
- [ ] Render inspect outputs, retain fictional data. APIs and dynamic chess generation deferred.

### Task 6: Review and executable
- [ ] Full tests, fresh reviewer of modules and whole branch; fix functional findings with regression tests.
- [ ] PyInstaller onefile build; test frozen program create/edit/save/reopen outside code tree.
- [ ] Deliver .exe plus source/fork branch, updated plan and evidence. Physical daily/cinema final check when authorized. Do not claim unperformed checks.

## Review Focus
Legacy documents and missing fields; portable image path handling; invalid/duplicate cuts; network partial writes and uncertain status; unsaved navigation and wrong-document overwrites. Every relevant task has regression tests. Preserve license, existing user data, and source repo.
