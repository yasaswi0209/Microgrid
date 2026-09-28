# Verification - sliding menu and question bank update

- Production build and lint passed.
- 33 Python tests passed. Coverage includes all 100 question texts and IDs, numerical forecast metrics, interval coverage, chronological split boundaries, model selection by validation MAE, and Windows disconnect handling.
- Six JavaScript calculation tests passed.
- Headless Chromium checks passed: all eight menu sections, desktop collapse/reopen, mobile drawer and Escape, closing after navigation, playback, alert review/filter, chatbot question search and replies, chat/CSV downloads, and theme persistence after reload.
- Desktop and mobile screenshots were inspected; no browser JavaScript errors or mobile horizontal overflow were detected in the checked flow.
- Forecasts were rebuilt from the original downloaded source CSV. Fixed additional candidates were selected by validation MAE only. Existing test-period comparison is reported transparently; it is not a new prospective evaluation.
- Data remains historical. No physical sensors, external LLM, current-day forecast or equipment-fault diagnosis is provided.

- Hosted static version: all 100 exact question answers matched the Python backend at three dataset positions (300 comparisons). The hosted build passed the same desktop/mobile browser flow.
- Questions PDF: six pages, exactly 100 numbered questions; all pages rendered and visually reviewed.
