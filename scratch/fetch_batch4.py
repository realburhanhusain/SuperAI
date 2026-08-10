import urllib.request
import os

repos = [
    "GoogleCloudPlatform/scion",
    "Shubhamsaboo/awesome-llm-apps",
    "EvoAgentX/EvoAgentX"
]

os.makedirs("scratch/readmes_v4", exist_ok=True)
out = open("scratch/summary_v4.md", "w", encoding="utf-8")

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
                with open(f"scratch/readmes_v4/{safe_name}.md", "w", encoding="utf-8") as f:
                    f.write(content)
                
                lines = content.split("\n")
                summary = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("<") and not line.startswith("[!") and "badge" not in line.lower() and "shield" not in line.lower():
                        summary.append(line)
                    if len(summary) > 50: 
                        break
                out.write("\n".join(summary) + "\n")
                
                success = True
                break
        except Exception:
            pass
out.close()
