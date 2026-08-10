import re

class OutputCompressor:
    @staticmethod
    def compress(text: str) -> str:
        """
        Compress text by stripping unnecessary whitespace and comments to save on token costs.
        """
        if not text:
            return text
            
        # Remove single-line comments (e.g., Python #, JS //)
        text = re.sub(r'(?m)^\s*#.*$', '', text)
        text = re.sub(r'(?m)^\s*//.*$', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()
