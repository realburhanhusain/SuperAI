import os
import glob

files = glob.glob("scratch/readmes/*.md")
with open("scratch/summary.md", "w", encoding="utf-8") as out:
    for f in files:
        repo = os.path.basename(f).replace(".md", "").replace("_", "/")
        out.write(f"\n{'='*60}\nREPO: {repo}\n{'='*60}\n")
        with open(f, "r", encoding="utf-8") as file:
            lines = file.readlines()
            
            summary = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("<") and not line.startswith("[!") and "badge" not in line.lower() and "shield" not in line.lower():
                    summary.append(line)
                if len(summary) > 20: 
                    break
            
            out.write("\n".join(summary) + "\n")
