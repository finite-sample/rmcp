# mcp/server/stdio.py

import sys
import json

def stdio_server(server):
    """
    Run the given server using standard input and output.
    Reads one JSON message per line from stdin and writes the JSON response to stdout.
    """
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            result = server.process_message(message)
            sys.stdout.write(json.dumps(result))
            sys.stdout.write("\n")
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": str(e)}
            sys.stdout.write(json.dumps(error_response))
            sys.stdout.write("\n")
            sys.stdout.flush()
