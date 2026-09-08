import http.server
import os
import re
import socketserver

PORT = 8080
DIRECTORY = "/Users/rd/Desktop/LexicalProject"

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            super().do_GET()
            return

        range_header = self.headers.get("Range")
        if not range_header:
            super().do_GET()
            return

        match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not match:
            super().do_GET()
            return

        file_size = os.path.getsize(path)
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else file_size - 1

        if start >= file_size:
            self.send_error(416, "Requested Range Not Satisfiable")
            return

        end = min(end, file_size - 1)
        length = end - start + 1

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()

        with open(path, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(length))

    def guess_type(self, path):
        if path.endswith(".wasm"): return "application/wasm"
        if path.endswith(".db"): return "application/octet-stream"
        if path.endswith(".json"): return "application/json"
        return super().guess_type(path)

print(f"[PWA SERVER] Serving at http://localhost:{PORT}/client/index.html with HTTP-206 Byte-Range support.")
try:
    with socketserver.TCPServer(("", PORT), RangeRequestHandler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\n[PWA SERVER] Stopped cleanly.")
