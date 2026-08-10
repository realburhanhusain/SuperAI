from src.core.surface_inventory import _function_calls
calls = _function_calls('src/cli/main.py')
q = [('status', [])]
visited = set()
while q:
    curr, path = q.pop(0)
    if curr in visited: continue
    visited.add(curr)
    for child in set(calls.get(curr, [])) - {'home'}:
        if child == 'SuperAIOrchestrator':
            print(path + [curr, child])
            exit(0)
        q.append((child, path + [curr]))
