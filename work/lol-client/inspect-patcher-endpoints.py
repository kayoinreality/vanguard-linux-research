"""Static public-bundle strings only: no process/session files or API calls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import runpy

library = runpy.run_path('/home/lab/lol-lab/inspect-asar-structure.py', run_name='asar_inspection_library')
archive = library['ARCHIVE']
with archive.open('rb') as source:
    source_hash = hashlib.file_digest(source, 'sha256').hexdigest()
if not source_hash.startswith('5d346'):
    raise ValueError('Archive hash prefix differs from authorized source')
archive_size, header_size, header_hash, entries = library['parse_header']()
scan_paths = ['dist/main/main.js', 'dist/renderer/renderer.js']
literal = re.compile(r'''(["'`])([^"'`\r\n]{1,240})\1''')
report = {'inspected_at_utc':datetime.now(timezone.utc).isoformat(),'archive_sha256':source_hash,'archive_bytes':archive_size,'scope':'Static public bundled JS only; no process arguments, auth configuration, lockfiles, private logs, API requests or UI changes.','files':{}}
for name in scan_paths:
    data = library['read_entry'](name, entries[name], header_size, archive_size, 16*1024*1024)
    code = data.decode('utf-8')
    endpoints = []
    seen = set()
    for match in literal.finditer(code):
        value = match[2]
        if value.startswith('/') and re.search(r'patch|download',value,re.I) and value not in seen:
            seen.add(value)
            endpoints.append({'path_literal':value,'character_offset':match.start(),'context':code[max(0,match.start()-180):match.end()+180]})
    terms = sorted(set(re.findall(r'\b[A-Za-z_$][A-Za-z0-9_$]*(?:[Pp]atch|[Pp]aus|[Pp]rogress|[Pp]hase|[Rr]eason)[A-Za-z0-9_$]*\b',code)))
    patcher_contexts = []
    for match in list(re.finditer(r'patcher',code,re.I))[:60]:
        patcher_contexts.append({'character_offset':match.start(),'context':code[max(0,match.start()-120):match.end()+180]})
    auth_contexts = []
    for pattern in [r'app-port',r'app-auth-token',r'remoting-auth-token',r'riotclient-auth-token',r'Authorization',r'Basic ',r'base64']:
        for match in list(re.finditer(pattern,code))[:5]:
            auth_contexts.append({'public_term':match[0],'character_offset':match.start(),'context':code[max(0,match.start()-100):match.end()+160]})
    report['files'][name] = {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'endpoint_literals':endpoints,'related_identifier_names':terms[:300],'patcher_contexts':patcher_contexts,'public_auth_contract_contexts':auth_contexts}
print(json.dumps(report,indent=2))
