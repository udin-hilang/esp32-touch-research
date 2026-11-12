"""Serve stored experiments as JSON over a small standard-library HTTP API."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from storage.experiment_store import DEFAULT_DATA_DIR, experiment_json, list_experiments


class ExperimentJSONHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = unquote(urlparse(self.path).path).strip("/").split("/")
        if route == ["api", "health"]:
            self._send_json({"status": "ok"})
            return

        if route == ["api", "experiments"]:
            experiments = list_experiments(self.server.data_dir)
            self._send_json({
                "count": len(experiments),
                "experiments": [
                    {
                        "folder": experiment["folder"],
                        "metadata": experiment["metadata"],
                        "sample_count": len(experiment["samples"]),
                        "errors": experiment["errors"],
                    }
                    for experiment in experiments
                ],
            })
            return

        if len(route) in (3, 4) and route[:2] == ["api", "experiments"]:
            folder = route[2]
            experiment = next(
                (item for item in list_experiments(self.server.data_dir) if item["folder"] == folder),
                None,
            )
            if experiment is None:
                self._send_json({"error": "Eksperimen tidak ditemukan"}, status=404)
                return
            if len(route) == 4 and route[3] == "metadata":
                self._send_json(experiment["metadata"])
                return
            if len(route) == 3:
                self._send_json(experiment_json(experiment))
                return

        self._send_json({
            "error": "Endpoint tidak ditemukan",
            "available": [
                "/api/health",
                "/api/experiments",
                "/api/experiments/<nama-folder>",
                "/api/experiments/<nama-folder>/metadata",
            ],
        }, status=404)

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


def main():
    parser = argparse.ArgumentParser(description="Serve stored experiment data as JSON")
    parser.add_argument("--host", default="127.0.0.1", help="Alamat bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port HTTP (default: 8765)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Direktori folder eksperimen")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ExperimentJSONHandler)
    server.data_dir = args.data_dir
    print(f"JSON API berjalan di http://{args.host}:{args.port}/api/experiments")
    print(f"Direktori data: {args.data_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
