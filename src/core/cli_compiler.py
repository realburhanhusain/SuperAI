import json
import sqlite3
import argparse
from pathlib import Path

class OpenAPICompiler:
    def __init__(self, db_path: str = "cli_cache.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS api_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                path TEXT NOT NULL,
                method TEXT NOT NULL,
                description TEXT,
                parameters TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def parse_spec(self, spec_path: str):
        with open(spec_path, 'r') as f:
            spec = json.load(f)
            
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        tool_name = spec.get('info', {}).get('title', 'default_cli').lower().replace(' ', '_')
        paths = spec.get('paths', {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                desc = details.get('description', '')
                params = json.dumps(details.get('parameters', []))
                
                c.execute('''
                    INSERT INTO api_endpoints (tool_name, path, method, description, parameters)
                    VALUES (?, ?, ?, ?, ?)
                ''', (tool_name, path, method.upper(), desc, params))
                
        conn.commit()
        conn.close()
        print(f"Successfully compiled {tool_name} CLI tools into {self.db_path}")

    def generate_cli_script(self, tool_name: str, output_path: str):
        script_content = f"""#!/usr/bin/env python3
import sqlite3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="{tool_name} CLI Tool")
    parser.add_argument('endpoint', help='The API endpoint to call')
    args = parser.parse_args()
    
    conn = sqlite3.connect('{self.db_path}')
    c = conn.cursor()
    c.execute('SELECT path, method, description FROM api_endpoints WHERE tool_name = ? AND path LIKE ?', ('{tool_name}', '%' + args.endpoint + '%'))
    results = c.fetchall()
    
    if not results:
        print("Endpoint not found.")
        sys.exit(1)
        
    for res in results:
        print(f"Path: {{res[0]}} | Method: {{res[1]}}")
        print(f"Description: {{res[2]}}")

if __name__ == '__main__':
    main()
"""
        with open(output_path, 'w') as f:
            f.write(script_content)
        print(f"Generated CLI script at {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenAPI to CLI Compiler")
    parser.add_argument("--spec", help="Path to OpenAPI JSON spec file", required=True)
    parser.add_argument("--out", help="Path to output CLI script", default="agent_cli.py")
    args = parser.parse_args()
    
    compiler = OpenAPICompiler()
    compiler.parse_spec(args.spec)
    compiler.generate_cli_script("default_cli", args.out)
