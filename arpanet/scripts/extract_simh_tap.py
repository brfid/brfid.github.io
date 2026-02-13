#!/usr/bin/env python3
import struct
import sys

def extract_simh_tap(tap_file):
    """Extract data from SIMH TAP format tape file."""
    with open(tap_file, 'rb') as f:
        records = []
        while True:
            # Read record length header (4 bytes, little-endian)
            header = f.read(4)
            if len(header) < 4:
                break
            
            record_len = struct.unpack('<I', header)[0]
            
            # Check for tape mark (0x00000000)
            if record_len == 0:
                print(f"Tape mark found")
                continue
            
            # Read the record data
            data = f.read(record_len)
            if len(data) < record_len:
                print(f"Incomplete record")
                break
            
            # Read record length trailer (should match header)
            trailer = f.read(4)
            if len(trailer) < 4:
                print(f"Missing trailer")
                break
            
            trailer_len = struct.unpack('<I', trailer)[0]
            if trailer_len != record_len:
                print(f"Length mismatch: {record_len} vs {trailer_len}")
            
            records.append(data)
            print(f"Record {len(records)}: {record_len} bytes")
        
        # Concatenate all records to form the tar file
        if records:
            tar_data = b''.join(records)
            with open('extracted.tar', 'wb') as out:
                out.write(tar_data)
            print(f"\nExtracted {len(tar_data)} bytes to extracted.tar")
            return True
    return False

if __name__ == '__main__':
    if extract_simh_tap('/tmp/transfer.tap'):
        print("Extraction successful")
    else:
        print("Extraction failed")
