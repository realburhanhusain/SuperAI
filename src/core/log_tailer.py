import os
from pathlib import Path
from typing import List

def tail_file(filepath: Path, lines: int = 100) -> List[str]:
    if not filepath.exists():
        return ["Log file not found."]
    try:
        with open(filepath, 'rb') as f:
            f.seek(0, 2)
            block_end_byte = f.tell()
            lines_to_go = lines
            block_number = -1
            data = []
            while lines_to_go > 0 and block_end_byte > 0:
                if (block_end_byte - 4096 > 0):
                    f.seek(block_number*4096, 2)
                    data.insert(0, f.read(4096))
                else:
                    f.seek(0,0)
                    data.insert(0, f.read(block_end_byte))
                lines_found = data[0].count(b'\n')
                lines_to_go -= lines_found
                block_end_byte -= 4096
                block_number -= 1
            all_read_text = b''.join(data).decode('utf-8', errors='replace')
            return all_read_text.splitlines()[-lines:]
    except Exception as e:
        return [f"Error reading logs: {e}"]