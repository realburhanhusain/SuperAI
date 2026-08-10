import os
import sqlite3
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

class AKBP:
    """
    Agent Knowledge Base Protocol (AKBP).
    Syncs memory to a local Obsidian vault (markdown files) and an FTS5-indexed SQLite db.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.brain_dir = self.workspace_root / ".superai" / "brain"
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.brain_dir / "index.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Create FTS5 virtual table for indexing
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    title, content, filepath UNINDEXED, created_at UNINDEXED
                )
            ''')
            conn.commit()

    def save_memory(self, title: str, content: str, tags: Optional[List[str]] = None) -> Path:
        """Save a memory as a markdown file in the Obsidian vault and index it in FTS5."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        safe_title = "".join([c if c.isalnum() else "_" for c in title])
        filename = f"{timestamp}_{safe_title}.md"
        filepath = self.brain_dir / filename
        
        tags_str = " ".join([f"#{t}" for t in (tags or [])])
        
        # Obsidian-compatible frontmatter
        md_content = f"---\ntitle: {title}\ndate: {timestamp}\ntags: {tags_str}\n---\n\n{content}\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memory_fts (title, content, filepath, created_at)
                VALUES (?, ?, ?, ?)
            ''', (title, content, str(filepath), timestamp))
            conn.commit()
            
        return filepath

    def search_memory(self, query: str) -> List[Dict[str, Any]]:
        """Search the indexed memories using FTS5 match."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title, content, filepath, created_at
                FROM memory_fts
                WHERE memory_fts MATCH ?
                ORDER BY rank
            ''', (query,))
            results = cursor.fetchall()
            
            return [
                {
                    "title": row[0],
                    "content": row[1],
                    "filepath": row[2],
                    "created_at": row[3]
                }
                for row in results
            ]
