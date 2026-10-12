from pathlib import Path
import struct
import zlib

root = Path(__file__).resolve().parent
width, height = 1024, 768
raw = (root / "console.rgb565").read_bytes()
if len(raw) == width * height * 2 + 4:
    raw = raw[4:]
assert len(raw) == width * height * 2, len(raw)
rows = bytearray()
for y in range(height):
    rows.append(0)
    for x in range(width):
        value = struct.unpack_from("<H", raw, (y * width + x) * 2)[0]
        rows.extend((((value >> 11) & 31) * 255 // 31, ((value >> 5) & 63) * 255 // 63, (value & 31) * 255 // 31))
def chunk(name, data):
    body = name + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
(root / "console.png").write_bytes(png)
print(str(root / "console.png"))
