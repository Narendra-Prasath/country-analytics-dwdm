"""
Entry point to launch the Country Analytics Interactive Web Dashboard.
"""

from __future__ import annotations

import sys
from web.app import app

if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    print(f"\n=======================================================")
    print(f" COUNTRY ANALYTICS INTERACTIVE DASHBOARD RUNNING")
    print(f" URL: http://127.0.0.1:{port}")
    print(f" Press Ctrl+C to terminate the server")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
