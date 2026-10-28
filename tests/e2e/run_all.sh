#!/usr/bin/env bash
# Run every browser check in order; stop at the first failure.
set -euo pipefail
cd "$(dirname "$0")"
for script in crawl.py booking_flow.py staff_event_flow.py register_and_mobile.py member_portal.py admin_flows.py membership_checkout.py; do
  echo "=== $script"
  python3 "$script"
done
echo "All browser checks passed."
