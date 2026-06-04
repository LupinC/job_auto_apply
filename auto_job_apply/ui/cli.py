from __future__ import annotations

import argparse
from pathlib import Path
import sys

from auto_job_apply.apply.adapters.autofill import request_shutdown as request_autofill_shutdown


def run_ui(host: str = "127.0.0.1", port: int = 8501) -> None:
	ui_entry = Path(__file__).resolve().parent / "streamlit_app.py"
	argv = [
		"streamlit",
		"run",
		str(ui_entry),
		"--server.address",
		host,
		"--server.port",
		str(port),
	]

	try:
		from streamlit.web import cli as stcli
	except ModuleNotFoundError as exc:
		raise RuntimeError("Streamlit is not installed. Install with: pip install streamlit") from exc

	prev_argv = sys.argv[:]
	try:
		sys.argv = argv
		stcli.main()
	except SystemExit as exc:
		code = 0 if exc.code is None else int(exc.code)
		if code not in (0, 130):
			raise RuntimeError(f"Streamlit exited with code {code}") from exc
	finally:
		request_autofill_shutdown()
		sys.argv = prev_argv


def main() -> None:
	parser = argparse.ArgumentParser(description="Launch Auto Job Apply Streamlit UI")
	parser.add_argument("--host", default="127.0.0.1", help="Streamlit host")
	parser.add_argument("--port", type=int, default=8501, help="Streamlit port")
	args = parser.parse_args()
	run_ui(host=args.host, port=args.port)


if __name__ == "__main__":
	main()
