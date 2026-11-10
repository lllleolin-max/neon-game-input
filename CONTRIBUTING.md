# Contributing

Install from source with `python -m pip install -e ".[neon,demo,browser,dev]"` on Python 3.12.
Run `python -m unittest discover -s tests -v` and `node --test tests/browser.test.mjs`.
Build using `python -m build`; smoke-test the wheel in a separate environment before releases.

Keep the core free of SDK/UI dependencies and update Python and browser sample semantics together.
Mark synthetic fixtures clearly. Hardware claims must identify the tested device, environment and
method, without including participant data or private identifiers. Do not equate local sample age
with end-to-end latency or synthetic projection tolerance with wearing accuracy.

For bug reports include package versions, operating system, entry point, observed status and minimal
steps. Redact addresses, device IDs and personal data. No video or raw gaze recording is needed for
ordinary connection reports. Keep changes focused and preserve the attribution notices.
