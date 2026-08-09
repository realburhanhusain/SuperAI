package get

import (
	"context"
	"sort"
	"strings"

	coreauth "github.com/router-for-me/CLIProxyAPIHome/internal/cliproxy/auth"
	"github.com/router-for-me/CLIProxyAPIHome/internal/registry"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
	"github.com/tidwall/sjson"
)

// handleModels handles a models.
func handleModels(ctx context.Context, env dispatch.Env, args []string) dispatch.Reply {
	// Normalize source data before building the derived payload.
	_ = ctx

	if len(args) != 2 {
		return dispatch.Err("wrong number of arguments for 'get' command")
	}

	if env.Runtime == nil || env.Runtime.CoreManager() == nil {
		return dispatch.Err("runtime not ready")
	}

	payload, errBuild := buildModelsJSON(env)
	if errBuild != nil {
		return dispatch.Err(errBuild.Error())
	}
	return dispatch.BulkString([]byte(payload))
}

// buildModelsJSON assembles the models payload grouped by provider bucket.
// Authentication is the caller's responsibility.
func buildModelsJSON(env dispatch.Env) (string, error) {
	if env.Runtime == nil || env.Runtime.CoreManager() == nil {
		return "", errRuntimeNotReady
	}

	resolveGroupKey := func(auth *coreauth.Auth) string {
		if auth == nil {
			return ""
		}
		provider := strings.ToLower(strings.TrimSpace(auth.Provider))
		if provider == "" {
			return ""
		}
		if provider != "codex" {
			return provider
		}
		planType := ""
		if auth.Attributes != nil {
			planType = strings.ToLower(strings.TrimSpace(auth.Attributes["plan_type"]))
		}
		switch planType {
		case "free":
			return "codex-free"
		case "plus":
			return "codex-plus"
		case "team", "business", "go":
			return "codex-team"
		case "pro", "":
			return "codex-pro"
		default:
			return "codex-pro"
		}
	}

	type modelBucket struct {
		byID map[string]*registry.ModelInfo
	}

	buckets := make(map[string]*modelBucket)
	addModel := func(groupKey string, model *registry.ModelInfo) {
		groupKey = strings.TrimSpace(groupKey)
		if groupKey == "" || model == nil {
			return
		}
		id := strings.TrimSpace(model.ID)
		if id == "" {
			return
		}
		idKey := strings.ToLower(id)
		b := buckets[groupKey]
		if b == nil {
			b = &modelBucket{byID: make(map[string]*registry.ModelInfo)}
			buckets[groupKey] = b
		}
		if _, exists := b.byID[idKey]; exists {
			return
		}
		b.byID[idKey] = model
	}

	reg := registry.GetGlobalRegistry()
	auths := env.Runtime.CoreManager().List()
	for _, auth := range auths {
		if auth == nil || auth.Disabled || auth.ID == "" {
			continue
		}
		groupKey := resolveGroupKey(auth)
		if groupKey == "" {
			continue
		}
		models := reg.GetModelsForClient(auth.ID)
		for _, model := range models {
			addModel(groupKey, model)
		}
	}

	out := "{}"
	groupKeys := make([]string, 0, len(buckets))
	for key := range buckets {
		groupKeys = append(groupKeys, key)
	}
	sort.Strings(groupKeys)

	for _, key := range groupKeys {
		b := buckets[key]
		if b == nil || len(b.byID) == 0 {
			continue
		}
		models := make([]*registry.ModelInfo, 0, len(b.byID))
		for _, model := range b.byID {
			models = append(models, model)
		}
		sort.Slice(models, func(i, j int) bool {
			idI := strings.ToLower(strings.TrimSpace(models[i].ID))
			idJ := strings.ToLower(strings.TrimSpace(models[j].ID))
			return idI < idJ
		})
		out, _ = sjson.Set(out, key, models)
	}
	return out, nil
}
