package diff

import (
	"testing"

	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
)

func TestDiffOAuthModelAliasChangesDetectsForceMapping(t *testing.T) {
	oldMap := map[string][]config.OAuthModelAlias{
		"claude": []config.OAuthModelAlias{
			{Name: "claude-sonnet-4", Alias: "sonnet"},
		},
	}
	newMap := map[string][]config.OAuthModelAlias{
		"claude": []config.OAuthModelAlias{
			{Name: "claude-sonnet-4", Alias: "sonnet", ForceMapping: true},
		},
	}

	changes, affected := DiffOAuthModelAliasChanges(oldMap, newMap)

	if len(changes) != 1 || changes[0] != "oauth-model-alias[claude]: updated (1 -> 1 entries)" {
		t.Fatalf("changes = %#v, want force-mapping update", changes)
	}
	if len(affected) != 1 || affected[0] != "claude" {
		t.Fatalf("affected = %#v, want claude", affected)
	}
}
