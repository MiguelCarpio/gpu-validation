#!/usr/bin/env python3
"""Print a server's serial console log via the OpenStack SDK.

Runs on the control node where openstacksdk + cloud auth are available. 
Usage:
    get_console_log.py <server_name_or_id> [cacert_path] [length]

On error, prints a single concise line to stderr.
"""
import sys

import openstack


def main():
    if len(sys.argv) < 2:
        print("usage: get_console_log.py <server> [cacert] [length]", file=sys.stderr)
        return 2
    server = sys.argv[1]
    cacert = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    length = int(sys.argv[3]) if len(sys.argv) > 3 else None

    # cacert makes the SDK trust the RHOSO self-signed CA, as the modules do.
    conn = openstack.connect(cacert=cacert) if cacert else openstack.connect()
    srv = conn.compute.find_server(server, ignore_missing=False)
    output = conn.compute.get_server_console_output(srv, length=length)
    # API returns {"output": "...."}
    print(output.get("output", "") if isinstance(output, dict) else output)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - concise error for a diagnostic tool
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(1)
