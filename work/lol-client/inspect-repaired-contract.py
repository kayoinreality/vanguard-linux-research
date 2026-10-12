"""Inspect public route identifiers in the repaired ASAR, without running it."""
import hashlib
import json
import re
import runpy

library = runpy.run_path('/home/lab/lol-lab/inspect-asar-structure.py', run_name='asar_inspection_library')
archive = library['ARCHIVE']
with archive.open('rb') as source:
    digest = hashlib.file_digest(source, 'sha256').hexdigest()
if digest != 'c59631b545fb11ccde204c901cb73bd9a7ba273e51e95cbf5f7ac51e606a7e60':
    raise SystemExit('Repaired archive identity mismatch')
archive_size, header_size, _, entries = library['parse_header']()
report = {'archive_sha256': digest, 'archive_bytes': archive_size, 'files': {}}
for name in ('dist/main/main.js', 'dist/renderer/renderer.js'):
    code = library['read_entry'](name, entries[name], header_size, archive_size, 16 * 1024 * 1024).decode('utf-8')
    literal = re.compile(r'''(["'`])([^"'`\r\n]{1,240})\1''')
    routes = sorted({match[2] for match in literal.finditer(code)
                     if match[2].startswith('/patch-proxy/') and
                     re.search(r'patch-states|products|patchlines', match[2])})
    terms = ('buildPatchProxyV2PatchStatesURI', 'usePatchStateV2', 'combined_patch_state',
             'totalBytesDownloaded', 'totalBytesToDownload', 'overallProgress', 'initHttpClient')
    report['files'][name] = {'patch_route_literals': routes,
                             'public_identifiers_present': [term for term in terms if term in code]}
print(json.dumps(report, indent=2))
