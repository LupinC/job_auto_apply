from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def run_ui(host: str = "127.0.0.1", port: int = 8501) -> None:
	ui_entry = Path(__file__).resolve().parent / "streamlit_app.py"
	cmd = [
		sys.executable,
		"-m",
		"streamlit",
		"run",
		str(ui_entry),
		"--server.address",
		host,
		"--server.port",
		str(port),
	]

	try:
		subprocess.run(cmd, check=True)
	except FileNotFoundError as exc:
		raise RuntimeError("Streamlit is not installed. Install with: pip install streamlit") from exc


def main() -> None:
	parser = argparse.ArgumentParser(description="Launch Auto Job Apply Streamlit UI")
	parser.add_argument("--host", default="127.0.0.1", help="Streamlit host")
	parser.add_argument("--port", type=int, default=8501, help="Streamlit port")
	args = parser.parse_args()
	run_ui(host=args.host, port=args.port)


if __name__ == "__main__":
	main()
