"""Report only connection categories; never print log lines or connection values."""
import json
from pathlib import Path
import re

lines = Path('/home/lab/lol-lab/ui-native.log').read_text(errors='replace').splitlines()
result = {'line_count': len(lines), 'websocket_events': {}}
for state in ('OPEN', 'CLOSE', 'ERROR'):
    matching = [index for index, line in enumerate(lines) if re.search(r'WebSocket.*event:\s*' + state, line, re.I)]
    result['websocket_events'][state] = {'count': len(matching), 'last_line_index': matching[-1] if matching else None}
result['foundation_connected_mentions'] = sum('renderer socket connected to Foundation' in line for line in lines)
print(json.dumps(result, indent=2))
