"""Read two verified local GET resources using the issued UI connection in memory.

Does not save connection values, alter vendor files, or change patcher state.
Only selected public status fields and classified error messages are exported.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import struct
import time
import urllib.error
import urllib.request

if os.getuid() != 1000:
    raise SystemExit('Invalid lab invocation')
archive = Path('/home/lab/lol-lab/prefix/drive_c/Riot Games/Riot Client/RiotClientElectron/resources/app.asar')
with archive.open('rb') as handle:
    archive_hash = hashlib.file_digest(handle, 'sha256').hexdigest()
    # Original collection and the official BR installer repair observed locally.
    if archive_hash not in {
        '5d346edfd1c69648643b2633ac75430db4722ad974b80521ff909759f26b88a6',
        'c59631b545fb11ccde204c901cb73bd9a7ba273e51e95cbf5f7ac51e606a7e60',
    }:
        raise SystemExit('Original ASAR identity mismatch')
with archive.open('rb') as handle:
    size_payload, header_size = struct.unpack('<II', handle.read(8))
    if size_payload != 4 or not 8 <= header_size <= 32 * 1024 * 1024:
        raise SystemExit('Invalid archive bounds')
    raw = handle.read(header_size)
    payload_size, string_size = struct.unpack_from('<II', raw)
    if string_size > payload_size - 4 or payload_size > header_size - 4:
        raise SystemExit('Invalid archive header')
    entry = json.loads(raw[8:8 + string_size])
    for segment in ('dist', 'main', 'root.pem'):
        entry = entry['files'][segment]
    size = entry['size']
    offset = 8 + header_size + int(entry['offset'])
    if entry.get('unpacked') or entry.get('link') or not 0 < size < 64 * 1024 or offset + size > archive.stat().st_size:
        raise SystemExit('Invalid certificate resource')
    handle.seek(offset)
    ca = handle.read(size).decode('ascii')
# Match the local Node HTTPS agent's CA policy. Keep certificate signatures,
# the supplied trust root, and hostname verification required. Python 3.14's
# convenience context adds strict legacy-certificate structure checks.
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(cadata=ca)

connections = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != os.getuid():
            continue
        args = (proc / 'cmdline').read_bytes().decode().rstrip('\0').split('\0')
        if not args or 'RiotClientElectron' not in args[0] or any(arg.startswith('--type=') for arg in args):
            continue
        if b'WINEPREFIX=/home/lab/lol-lab/prefix' not in (proc / 'environ').read_bytes().split(b'\0'):
            continue
        if b'lol-lab-client.service' not in (proc / 'cgroup').read_bytes():
            continue
        values = dict(arg[2:].split('=', 1) for arg in args[1:] if arg.startswith('--') and '=' in arg)
        port, token = values.get('app-port', ''), values.get('remoting-auth-token', '')
        if port.isdigit() and 1 <= int(port) <= 65535 and token:
            connections.append((int(port), token))
    except (OSError, UnicodeError):
        pass
if len(connections) != 1:
    raise SystemExit('Unique owned UI connection not available')
port, token = connections[0]
authorization = 'Basic ' + base64.b64encode(('riot:' + token).encode()).decode()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))

def enum(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z][A-Za-z_ -]{0,63}', value) else None

def progress(value):
    keys = ('totalBytesDownloaded', 'totalBytesToDownload', 'overallProgress', 'downloaded_bytes', 'bytes_to_download', 'progress', 'percentage')
    return {key: value[key] for key in keys if isinstance(value, dict) and type(value.get(key)) in (int, float)}

def status(value):
    if not isinstance(value, dict):
        return {'type': type(value).__name__}
    result = {}
    for key in ('launchable',):
        if type(value.get(key)) is bool:
            result[key] = value[key]
    for key in ('state', 'combined_patch_state', 'repair_code', 'repairCode', 'repairReason', 'previousState'):
        if enum(value.get(key)) is not None:
            result[key] = enum(value[key])
        elif key in ('repair_code', 'repairCode') and type(value.get(key)) is int:
            result[key] = value[key]
    if isinstance(value.get('progress'), dict):
        result['progress'] = progress(value['progress'])
        if enum(value['progress'].get('phase')):
            result['progress']['phase'] = enum(value['progress']['phase'])
        if isinstance(value['progress'].get('update'), dict):
            result['progress']['update'] = progress(value['progress']['update'])
    if isinstance(value.get('patch_status'), dict):
        result['patch_status'] = status(value['patch_status'])
    if isinstance(value.get('dependency_status'), dict):
        result['dependency_status'] = status(value['dependency_status'])
    elif 'dependency_status' in value:
        result['dependency_status_type'] = type(value['dependency_status']).__name__
    if isinstance(value.get('error'), dict):
        error = value['error']
        result['error'] = {'code': enum(error.get('code')) if type(error.get('code')) is not int else error['code']}
        message = error.get('message', '')
        categories = {'disk_space': r'disk.*(?:full|space)|insufficient.*space', 'permission': r'permission|access.denied', 'missing_file': r'not.found|missing.file', 'cross_device': r'cross.device|same.device|EXDEV', 'checksum': r'checksum|hash.mismatch', 'connection': r'connection|network', 'timeout': r'timeout|timed.out', 'vanguard': r'vanguard|vgk|vgc', 'dependency': r'dependen'}
        result['error']['message_categories'] = [name for name, pattern in categories.items() if isinstance(message, str) and re.search(pattern, message, re.I)]
    result['public_schema_keys'] = [key for key in value if isinstance(key, str) and re.fullmatch(r'[a-zA-Z][a-zA-Z_]{0,39}', key) and not re.search(r'auth|token|secret|session|account|user|player|credential|email|password', key, re.I)]
    return result

report = {'observed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'method': 'GET', 'archive_sha256': archive_hash, 'local_tls_ca': 'original ASAR dist/main/root.pem', 'certificate_validation_enabled': context.verify_mode == ssl.CERT_REQUIRED, 'hostname_validation_enabled': context.check_hostname, 'x509_verify_flags': int(context.verify_flags), 'resources': []}
for version in ('v2', 'v1'):
    path = f'/patch-proxy/{version}/patch-states/products/league_of_legends/patchlines/live'
    item = {'resource': path}
    request = urllib.request.Request(f'https://127.0.0.1:{port}' + path, headers={'Authorization': authorization, 'Accept': 'application/json'}, method='GET')
    try:
        with opener.open(request, timeout=10) as response:
            data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError('Response exceeds diagnostic bound')
            item['http_status'] = response.status
            item['state'] = status(json.loads(data))
    except urllib.error.HTTPError as error:
        item['http_status'] = error.code
    except Exception as error:
        item['error_type'] = type(error).__name__
        reason = getattr(error, 'reason', error)
        if isinstance(reason, ssl.SSLCertVerificationError):
            item['tls_verify_code'] = reason.verify_code
    report['resources'].append(item)
print(json.dumps(report, indent=2))
