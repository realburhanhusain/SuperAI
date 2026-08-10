import urllib.request
import os

repos = [
    "rohitg00/agentmemory", "rohitg00/pro-workflow", "rohitg00/graphify", 
    "rohitg00/oh-my-harness", "rohitg00/awesome-llm-apps", "rohitg00/workers", 
    "rohitg00/orca", "stablyai/orca", "rohitg00/awesome-openclaw", 
    "openclaw/openclaw", "agentgateway/agentgateway", "getkimchi/kimchi", 
    "rohitg00/skillkit", "rohitg00/agentbrain", "rohitg00/external-agents", 
    "pingdotgg/t3code", "vercel-labs/zerolang", "rohitg00/akbp", 
    "rohitg00/openbuild", "rohitg00/agent-doctor", "tinyhumansai/openhuman", 
    "ghostty-org/ghostty", "rohitg00/rimuru", "rohitg00/Archon", 
    "coleam00/Archon", "gitbutlerapp/gitbutler"
]

os.makedirs("scratch/readmes", exist_ok=True)

for repo in repos:
    print(f"Fetching {repo}...")
    success = False
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                content = response.read().decode("utf-8")
                safe_name = repo.replace("/", "_")
                with open(f"scratch/readmes/{safe_name}.md", "w", encoding="utf-8") as f:
                    f.write(content)
                success = True
                print(f"  -> Downloaded from {branch}")
                break
        except Exception as e:
            pass
    if not success:
        print(f"  -> Failed to download {repo}")

