import urllib.request
import os
import json

repos = [
    "chenglou/pretext",
    "manaflow-ai/cmux",
    "manaflow-ai/manaflow",
    "manaflow-ai/subrouter",
    "manaflow-ai/pi-codex",
    "manaflow-ai/cmux-home",
    "manaflow-ai/sandbox-agent",
    "karpathy/autoresearch",
    "karpathy/nanochat",
    "karpathy/micrograd",
    "rohitg00/n-autoresearch",
    "Conway-Research/automaton",
    "K-Dense-AI/scientific-agent-skills",
    "iii-hq/iii",
    "iii-hq/workers",
    "paperclipai/paperclip"
]

os.makedirs("scratch/readmes_v3", exist_ok=True)
out = open("scratch/summary_v3.md", "w", encoding="utf-8")

for repo in repos:
    success = False
    out.write(f"\n{'='*60}\nREPO: {repo}\n{'='*60}\n")
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                content = response.read().decode("utf-8")
                safe_name = repo.replace("/", "_")
                with open(f"scratch/readmes_v3/{safe_name}.md", "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Write summary snippet
                lines = content.split("\n")
                summary = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("<") and not line.startswith("[!") and "badge" not in line.lower() and "shield" not in line.lower():
                        summary.append(line)
                    if len(summary) > 30: 
                        break
                out.write("\n".join(summary) + "\n")
                
                success = True
                break
        except Exception as e:
            pass
out.close()
