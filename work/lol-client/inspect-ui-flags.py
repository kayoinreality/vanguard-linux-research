import mmap
from pathlib import Path

path = Path('/home/lab/lol-lab/prefix/drive_c/Riot Games/Riot Client/RiotClientElectron/resources/app.asar')
with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
    for pattern in (b'const getInstallSettings=', b'function getInstallSettings', b'installSettings.json', b'InstallSettings.json'):
        start = 0
        for _ in range(4):
            index = data.find(pattern, start)
            if index < 0:
                break
            print(pattern.decode(), hex(index), data[max(0, index-30):index+len(pattern)+900].decode(errors='replace'))
            start = index + len(pattern)
