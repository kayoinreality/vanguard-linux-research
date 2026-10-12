"""Inspect a bounded callee region in an owned PE sample; never load it."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'work/vanguard-estudo/samples/vgk.sys'
REPORT = ROOT / 'outputs/vgk-callee-estatico.json'
CONTEXT = ROOT / 'work/vanguard-estudo/vgk-callee-context.bin'
JUMP_CONTEXT = ROOT / 'work/vanguard-estudo/vgk-jump-context.bin'
EXPECTED_HASH = '8ba32cfbc4a07fd41a082344e23e312515ffafef0e568ba72e7d33e83b558f13'
TARGET_RVA = 0x061B9E27
PREFERRED_BASE = 0x140000000
MAX_CONTEXT = 512


def main():
    data = SOURCE.read_bytes()
    source_hash = hashlib.sha256(data).hexdigest()
    if source_hash != EXPECTED_HASH:
        raise ValueError('Sample hash differs from the authorized source')

    def unpack(fmt, offset):
        if not 0 <= offset <= len(data) - struct.calcsize(fmt):
            raise ValueError('Out-of-file field')
        result = struct.unpack_from(fmt, data, offset)
        return result[0] if len(result) == 1 else result

    if data[:2] != b'MZ':
        raise ValueError('Not MZ')
    pe = unpack('<I', 0x3c)
    if data[pe:pe+4] != b'PE\0\0' or unpack('<H', pe+4) != 0x8664:
        raise ValueError('Not an AMD64 PE image')
    optional = pe+24
    optional_size = unpack('<H', pe+20)
    if unpack('<H', optional) != 0x20b or optional_size < 144:
        raise ValueError('Not a PE32+ header with exception directory')
    image_base = unpack('<Q', optional+24)
    if image_base != PREFERRED_BASE:
        raise ValueError('Unexpected preferred image base')
    sections = []
    for index in range(unpack('<H', pe+6)):
        offset = optional+optional_size+index*40
        sections.append({
            'name': data[offset:offset+8].split(b'\0',1)[0].decode('ascii','replace'),
            'virtual_size': unpack('<I',offset+8), 'rva': unpack('<I',offset+12),
            'raw_size': unpack('<I',offset+16), 'raw_offset': unpack('<I',offset+20),
            'characteristics': unpack('<I',offset+36),
        })

    def mapping(rva, length=1):
        matches = []
        for section in sections:
            delta = rva-section['rva']
            if 0 <= delta and delta+length <= section['raw_size']:
                offset = section['raw_offset']+delta
                if offset+length <= len(data):
                    matches.append((offset, section))
        if len(matches) != 1:
            raise ValueError(f'RVA mapping is absent or ambiguous: {rva:#x}+{length}')
        return matches[0]

    target_offset, target_section = mapping(TARGET_RVA)
    exception_rva, exception_size = unpack('<II',optional+112+3*8)
    exception_offset, exception_section = mapping(exception_rva,exception_size)
    records = []
    all_records = []
    for index in range(exception_size//12):
        record_offset = exception_offset+12*index
        begin,end,unwind = unpack('<III',record_offset)
        all_records.append({'table_index_zero_based': index, 'table_record_file_offset': record_offset, 'begin_rva': begin, 'end_rva_exclusive': end, 'unwind_rva': unwind})
        if begin <= TARGET_RVA < end:
            record = {
                'table_index_zero_based': index, 'table_record_file_offset': record_offset,
                'record_bytes_hex': data[record_offset:record_offset+12].hex(),
                'begin_rva': begin, 'end_rva_exclusive': end, 'unwind_rva': unwind,
                'target_equals_begin': TARGET_RVA == begin, 'target_offset_from_begin': TARGET_RVA-begin,
            }
            try:
                unwind_offset, unwind_section = mapping(unwind,4)
                raw_header = data[unwind_offset:unwind_offset+4]
                record['unwind_header'] = {
                    'file_offset': unwind_offset, 'section': unwind_section['name'],
                    'bytes_hex': raw_header.hex(), 'version': raw_header[0]&7,
                    'flags': raw_header[0]>>3, 'prolog_size': raw_header[1],
                    'count_of_2byte_slots': raw_header[2], 'frame_register': raw_header[3]&15,
                    'frame_offset_units_16bytes': raw_header[3]>>4,
                    'limitation': 'Header bitfields only; unwind opcodes, handlers and chaining not interpreted.',
                }
            except ValueError as error:
                record['unwind_mapping_error'] = str(error)
            records.append(record)

    start = TARGET_RVA
    if len(records) == 1 and 0 <= TARGET_RVA-records[0]['begin_rva'] <= 128:
        start = records[0]['begin_rva']
    end = min(start+MAX_CONTEXT, target_section['rva']+target_section['raw_size'])
    if len(records) == 1:
        end = min(end,records[0]['end_rva_exclusive'])
    if not start <= TARGET_RVA < end:
        raise ValueError('The bounded context would not include the target')
    context_offset, context_section = mapping(start,end-start)
    context = data[context_offset:context_offset+end-start]
    CONTEXT.write_bytes(context)
    previous = max((record for record in all_records if record['end_rva_exclusive'] <= TARGET_RVA),key=lambda record:record['end_rva_exclusive'],default=None)
    following = min((record for record in all_records if record['begin_rva'] > TARGET_RVA),key=lambda record:record['begin_rva'],default=None)
    initial_jump = None
    if data[target_offset] == 0xe9:
        displacement = unpack('<i',target_offset+1)
        jump_rva = TARGET_RVA+5+displacement
        jump_records = [record for record in all_records if record['begin_rva'] <= jump_rva < record['end_rva_exclusive']]
        initial_jump = {'opcode': 'E9 rel32', 'instruction_bytes_hex': data[target_offset:target_offset+5].hex(), 'source_rva':TARGET_RVA,'source_preferred_va':image_base+TARGET_RVA,'instruction_bytes':5,'signed_displacement':displacement,'next_rva':TARGET_RVA+5,'target_rva':jump_rva,'target_preferred_va':image_base+jump_rva,'runtime_function_candidates_covering_target':jump_records}
        try:
            jump_offset,jump_section = mapping(jump_rva)
            jump_end = min(jump_rva+128,jump_section['rva']+jump_section['raw_size'])
            if len(jump_records) == 1:
                jump_end = min(jump_end,jump_records[0]['end_rva_exclusive'])
            mapping(jump_rva,jump_end-jump_rva)
            jump_bytes = data[jump_offset:jump_offset+jump_end-jump_rva]
            JUMP_CONTEXT.write_bytes(jump_bytes)
            initial_jump['target_mapping'] = {'file_offset':jump_offset,'section':jump_section}
            initial_jump['context'] = {'start_rva':jump_rva,'end_rva_exclusive':jump_end,'start_preferred_va':image_base+jump_rva,'end_preferred_va_exclusive':image_base+jump_end,'file_offset':jump_offset,'file_end_offset_exclusive':jump_offset+len(jump_bytes),'bytes':len(jump_bytes),'sha256':hashlib.sha256(jump_bytes).hexdigest(),'bytes_hex':jump_bytes.hex()}
            for record in jump_records:
                try:
                    unwind_offset,unwind_section = mapping(record['unwind_rva'],4)
                    raw_header = data[unwind_offset:unwind_offset+4]
                    record['unwind_header'] = {'file_offset':unwind_offset,'section':unwind_section['name'],'bytes_hex':raw_header.hex(),'version':raw_header[0]&7,'flags':raw_header[0]>>3,'prolog_size':raw_header[1],'count_of_2byte_slots':raw_header[2],'frame_register':raw_header[3]&15,'frame_offset_units_16bytes':raw_header[3]>>4,'limitation':'Header bitfields only; unwind opcodes, handlers and chaining not interpreted.'}
                except ValueError as error:
                    record['unwind_mapping_error'] = str(error)
        except ValueError as error:
            initial_jump['target_mapping_error'] = str(error)
    result = {
        'inspected_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': {'path': str(SOURCE), 'bytes': len(data), 'sha256': source_hash},
        'machine': 'AMD64', 'image_base_preferred': image_base,
        'target': {'preferred_va': image_base+TARGET_RVA, 'rva': TARGET_RVA, 'file_offset': target_offset, 'section': target_section},
        'exception_directory': {'rva':exception_rva,'bytes':exception_size,'file_offset':exception_offset,'section':exception_section['name'], 'candidate_records':exception_size//12,'trailing_bytes':exception_size%12},
        'runtime_function_candidates_covering_target': records,
        'nearest_runtime_function_candidates': {'previous_ending_at_or_before_target':previous,'next_beginning_after_target':following},
        'initial_direct_jump': initial_jump,
        'context': {'start_rva':start,'end_rva_exclusive':end,'start_preferred_va':image_base+start,'end_preferred_va_exclusive':image_base+end,'file_offset':context_offset,'file_end_offset_exclusive':context_offset+len(context),'bytes':len(context),'sha256':hashlib.sha256(context).hexdigest(),'section':context_section['name'],'bytes_hex':context.hex()},
        'limitations': ['Static read only; no driver loaded, executed, patched or runtime-unpacked.', 'A RUNTIME_FUNCTION-shaped entry is a location candidate; no code/unwind correctness or reachability is established.', 'A disassembler can decode data as instructions; purpose and dynamic behavior are not inferred.'],
    }
    REPORT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
