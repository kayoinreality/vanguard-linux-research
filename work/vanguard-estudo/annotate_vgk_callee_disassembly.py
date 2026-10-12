"""Verify displayed bytes against bounded static copies and record transfers."""
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'outputs/vgk-callee-estatico.json'
TEXT = ROOT / 'outputs/vgk-callee-estatico.txt'


def main():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    source = Path(report['source']['path'])
    reference_rva = 0x061c2151
    section = report['target']['section']
    reference_offset = section['raw_offset']+reference_rva-section['rva']
    if not section['rva'] <= reference_rva <= section['rva']+section['raw_size']-5:
        raise ValueError('Entry reference is outside the mapped section')
    with source.open('rb') as file:
        file.seek(reference_offset)
        reference_bytes = file.read(5)
        if len(reference_bytes) != 5 or reference_bytes[0] != 0xe8:
            raise ValueError('Entry reference is not E8 rel32')
        displacement = struct.unpack_from('<i',reference_bytes,1)[0]
        if reference_rva+5+displacement != report['target']['rva']:
            raise ValueError('Entry reference points to a different target')
        report['entry_reference_call'] = {'rva':reference_rva,'preferred_va':report['image_base_preferred']+reference_rva,'file_offset':reference_offset,'instruction_bytes_hex':reference_bytes.hex(),'signed_displacement':displacement,'target_rva':reference_rva+5+displacement,'target_preferred_va':report['image_base_preferred']+reference_rva+5+displacement}
        for record in report['initial_direct_jump']['runtime_function_candidates_covering_target']:
            file.seek(record['table_record_file_offset'])
            raw = file.read(12)
            if struct.unpack('<III',raw) != (record['begin_rva'],record['end_rva_exclusive'],record['unwind_rva']):
                raise ValueError('Runtime function candidate bytes mismatch')
            record['record_bytes_hex'] = raw.hex()
    text = TEXT.read_text(encoding='utf-8')
    originals = report['context']
    extension = report['initial_direct_jump']['context']
    ranges = [
        ('original_512byte_context', originals, bytes.fromhex(originals['bytes_hex'])),
        ('initial_jump_target_128byte_context', extension, bytes.fromhex(extension['bytes_hex'])),
    ]
    summaries = {name:{'displayed_bytes':0,'decoded_lines_with_assembly':0,'lines_marked_bad':0,'byte_directive_lines':0} for name,_,_ in ranges}
    transfers = []
    tool = text.splitlines()[0].removeprefix('# Tool: ')
    for line in text.splitlines():
        match = re.match(r'^\s*([0-9a-f]+):\t([0-9a-f ]+)(?:\t(.*))?$', line, re.I)
        if not match:
            continue
        address = int(match[1],16)
        chunk = bytes.fromhex(match[2])
        assembly = (match[3] or '').strip()
        group = next(((name,metadata,data) for name,metadata,data in ranges if metadata['start_preferred_va'] <= address < metadata['end_preferred_va_exclusive']),None)
        if group is None:
            raise ValueError('Disassembly chunk outside bounded source context')
        name,metadata,data = group
        relative = address-metadata['start_preferred_va']
        summary = summaries[name]
        if relative != summary['displayed_bytes'] or data[relative:relative+len(chunk)] != chunk:
            raise ValueError('Displayed bytes differ from source or are not contiguous')
        summary['displayed_bytes'] += len(chunk)
        summary['decoded_lines_with_assembly'] += bool(assembly)
        summary['lines_marked_bad'] += '(bad)' in assembly
        summary['byte_directive_lines'] += assembly.startswith('.byte')
        transfer = re.search(r'(?:^|\s)(call|jmp|j[a-z]+|loop[a-z]*|retf?|iret[q]?)\s*(.*)$',assembly)
        if transfer:
            mnemonic,operand = transfer.groups()
            immediate = re.fullmatch(r'0x([0-9a-f]+)',operand,re.I)
            target = int(immediate[1],16) if immediate and not mnemonic.startswith(('ret','iret')) else None
            direct = target is not None
            if name == ranges[0][0]:
                status = 'initial_direct_jump' if address == originals['start_preferred_va'] else 'linear_context_after_unconditional_jump_no_reachability_established'
            else:
                status = 'prefix_before_or_at_first_indirect_jump' if address <= extension['start_preferred_va']+21 else 'linear_context_after_indirect_jump_no_reachability_established'
            transfers.append({'context':name,'preferred_va':address,'rva':address-report['image_base_preferred'],'displayed_instruction_bytes_hex':chunk.hex(),'mnemonic':mnemonic,'operand':operand,'direct_target_preferred_va':target,'direct_target_rva':target-report['image_base_preferred'] if target is not None else None,'classification':'direct' if direct else 'return' if mnemonic.startswith(('ret','iret')) else 'indirect','evidence_scope':status})
    for name,metadata,_ in ranges:
        if summaries[name]['displayed_bytes'] != metadata['bytes']:
            raise ValueError('The displayed context does not cover the complete bounded source')
    report['disassembly'] = {'tool':tool,'text_artifact':str(TEXT),'byte_verification':'All displayed byte chunks are contiguous and equal to the exact source contexts.','contexts':summaries,'observed_control_transfers':transfers,'limitation':'Linear decoding, especially after unconditional jumps, is not proof of executable code or reachability. No direct-call target after the authorized initial E9 target was followed.'}
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'tool':tool,'contexts':summaries,'control_transfer_count':len(transfers),'original_rva':hex(report['target']['rva']),'original_offset':hex(report['target']['file_offset']),'original_context_end':hex(originals['end_preferred_va_exclusive']),'jump_target_rva':hex(report['initial_direct_jump']['target_rva']),'jump_target_offset':hex(report['initial_direct_jump']['target_mapping']['file_offset']),'jump_context_end':hex(extension['end_preferred_va_exclusive']),'jump_candidates':[{key:hex(record[key]) for key in ('begin_rva','end_rva_exclusive','unwind_rva','table_record_file_offset')} for record in report['initial_direct_jump']['runtime_function_candidates_covering_target']],'neighbor_records':{name:{key:hex(record[key]) for key in ('begin_rva','end_rva_exclusive','unwind_rva','table_record_file_offset')} for name,record in report['nearest_runtime_function_candidates'].items() if record}},indent=2))


if __name__ == '__main__':
    main()
