"""Read-only connection check; no video, gaze coordinates, or device IDs saved."""
import argparse
from collections import Counter
import json
import math
import time

from . import NeonInput, Surface


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", help="Companion host/IP; omit for discovery")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--seconds", type=float, default=15)
    args = parser.parse_args(argv)
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("seconds must be positive and finite")
    counts, seen, connected = Counter(), None, False
    # Use while a demo displays these same markers, with its own Neon reader stopped.
    with NeonInput(Surface(), address=args.address, port=args.port) as neon:
        deadline = time.monotonic()+args.seconds
        try:
            while time.monotonic() < deadline:
                connected |= neon.connected
                sample = neon.poll()
                if sample and sample.sequence != seen:
                    seen = sample.sequence
                    counts["valid_mapped" if sample.valid and sample.mapped else sample.reason] += 1
                    if sample.reason == "dependency_missing":
                        break
                time.sleep(0.02)
        except KeyboardInterrupt:
            pass
    print(json.dumps({"sdk_connected": connected, "samples_by_state": dict(counts),
                      "note": "Connection is separate from screen mapping. No hardware accuracy claim."}, indent=2))
    return 0 if connected else 1


if __name__ == "__main__":
    raise SystemExit(main())
