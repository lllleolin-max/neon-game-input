# Standalone project

This repository is independent of the Lingnan game from which its input concepts
were extracted. Do not import from, reference at runtime, or modify that project.
Keep the core importable with only Python's standard library. SDK, Pygame, and
aiohttp imports belong inside their optional adapters/entry points.

Never call simulated input a connected Neon. Keep scene video local and transient.
The browser must execute its own game, not receive streamed game frames. Do not
commit participant records, device addresses, credentials, virtual environments,
or private diagnostics. Preserve upstream attribution.

Run `python -m unittest discover -s tests -v`, `node --test tests/browser.test.mjs`,
and package/install smoke checks when changing the input contract or packaging.
Official mapper tests require the neon extra; a skip is not a pass on hardware.
Update both examples when changing the shared sample contract.
