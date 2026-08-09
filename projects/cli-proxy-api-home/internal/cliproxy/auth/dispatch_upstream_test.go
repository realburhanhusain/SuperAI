package auth

import (
	"context"
	"net/http"
	"testing"
	"time"

	internalconfig "github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/registry"
)

type firstCandidateSelector struct{}

func (firstCandidateSelector) Pick(_ context.Context, _ string, _ string, _ Options, auths []*Auth) (*Auth, error) {
	if len(auths) == 0 {
		return nil, nil
	}
	return auths[0], nil
}

type orderedCandidateSelector struct {
	order []string
}

func (s orderedCandidateSelector) Pick(_ context.Context, _ string, _ string, _ Options, auths []*Auth) (*Auth, error) {
	if len(auths) == 0 {
		return nil, nil
	}

	byID := make(map[string]*Auth, len(auths))
	for _, auth := range auths {
		if auth != nil {
			byID[auth.ID] = auth
		}
	}
	for _, id := range s.order {
		if auth := byID[id]; auth != nil {
			return auth, nil
		}
	}
	return auths[0], nil
}

type dispatchTestFullAuthResolver struct {
	auths map[string]*Auth
}

func (r dispatchTestFullAuthResolver) GetFullAuth(_ context.Context, uuid string) (*Auth, error) {
	auth := r.auths[uuid]
	if auth == nil {
		return nil, ErrFullAuthNotFound
	}
	return auth.Clone(), nil
}

func registerDispatchTestModel(t *testing.T, authID, provider string, models ...string) {
	t.Helper()
	infos := make([]*registry.ModelInfo, 0, len(models))
	for _, model := range models {
		infos = append(infos, &registry.ModelInfo{ID: model, Object: "model", OwnedBy: provider, Type: provider})
	}
	registry.GetGlobalRegistry().RegisterClient(authID, provider, infos)
	t.Cleanup(func() {
		registry.GetGlobalRegistry().UnregisterClient(authID)
	})
}

func registerDispatchTestAuth(t *testing.T, manager *Manager, auth *Auth, models ...string) {
	t.Helper()
	registerDispatchTestModel(t, auth.ID, auth.Provider, models...)
	if _, errRegister := manager.Register(context.Background(), auth); errRegister != nil {
		t.Fatalf("Register(%s) error = %v", auth.ID, errRegister)
	}
}

func geminiAPIKeyAuth(id, apiKey string, priority string) *Auth {
	return &Auth{
		ID:       id,
		Provider: "gemini",
		Status:   StatusActive,
		Attributes: map[string]string{
			"api_key":  apiKey,
			"priority": priority,
		},
	}
}

func setGeminiAliasConfig(manager *Manager) {
	manager.SetConfig(&internalconfig.Config{
		GeminiKey: []internalconfig.GeminiKey{
			{
				APIKey: "high-key",
				Models: []internalconfig.GeminiModel{
					{Name: "upstream-shared", Alias: "alias-a"},
					{Name: "upstream-shared", Alias: "alias-b"},
				},
			},
			{
				APIKey: "low-key",
				Models: []internalconfig.GeminiModel{
					{Name: "upstream-shared", Alias: "alias-a"},
					{Name: "upstream-shared", Alias: "alias-b"},
				},
			},
			{
				APIKey: "other-key",
				Models: []internalconfig.GeminiModel{
					{Name: "upstream-other", Alias: "alias-b"},
				},
			},
		},
	})
}

func markQuota429(t *testing.T, manager *Manager, authID, upstreamModel string) {
	t.Helper()
	manager.MarkResult(context.Background(), Result{
		AuthID:  authID,
		Model:   upstreamModel,
		Success: false,
		Error: &Error{
			Message:    "quota exhausted",
			HTTPStatus: http.StatusTooManyRequests,
		},
	})

	got, ok := manager.GetByID(authID)
	if !ok || got == nil {
		t.Fatalf("GetByID(%s) missing auth after MarkResult", authID)
	}
	modelKey := canonicalModelKey(upstreamModel)
	state := got.ModelStates[modelKey]
	if state == nil {
		t.Fatalf("ModelStates[%s] missing after MarkResult: %#v", modelKey, got.ModelStates)
	}
	next := time.Now().Add(time.Hour)
	state.NextRetryAfter = next
	state.Quota.NextRecoverAt = next
	if _, errUpdate := manager.Update(context.Background(), got); errUpdate != nil {
		t.Fatalf("Update(%s) error = %v", authID, errUpdate)
	}
}

func TestDispatchFastPathUsesUpstreamCooldownAcrossAliases(t *testing.T) {
	manager := NewManager(nil, nil, nil)
	setGeminiAliasConfig(manager)
	high := geminiAPIKeyAuth("upstream-fast-high", "high-key", "10")
	low := geminiAPIKeyAuth("upstream-fast-low", "low-key", "1")
	registerDispatchTestAuth(t, manager, high, "alias-a", "alias-b")
	registerDispatchTestAuth(t, manager, low, "alias-a", "alias-b")

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-a", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-a) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != high.ID {
		t.Fatalf("Dispatch(alias-a) auth = %#v, want %s", decision, high.ID)
	}
	if decision.UpstreamModel != "upstream-shared" {
		t.Fatalf("Dispatch(alias-a) upstream = %q, want upstream-shared", decision.UpstreamModel)
	}

	markQuota429(t, manager, high.ID, "upstream-shared")

	decision, errDispatch = manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != low.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s after upstream cooldown", decision, low.ID)
	}
}

func TestDispatchFastPathResetsShardAfterConfigChange(t *testing.T) {
	manager := NewManager(nil, nil, nil)
	setGeminiAliasConfig(manager)
	high := geminiAPIKeyAuth("upstream-reset-high", "high-key", "10")
	low := geminiAPIKeyAuth("upstream-reset-low", "low-key", "1")
	next := time.Now().Add(time.Hour)
	high.ModelStates = map[string]*ModelState{
		"upstream-changed": {
			Status:         StatusError,
			Unavailable:    true,
			NextRetryAfter: next,
			Quota: QuotaState{
				Exceeded:      true,
				NextRecoverAt: next,
			},
		},
	}
	registerDispatchTestAuth(t, manager, high, "alias-b")
	registerDispatchTestAuth(t, manager, low, "alias-b")

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != high.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s", decision, high.ID)
	}
	if decision.UpstreamModel != "upstream-shared" {
		t.Fatalf("Dispatch(alias-b) upstream = %q, want upstream-shared", decision.UpstreamModel)
	}

	manager.SetConfig(&internalconfig.Config{
		GeminiKey: []internalconfig.GeminiKey{
			{
				APIKey: "high-key",
				Models: []internalconfig.GeminiModel{
					{Name: "upstream-changed", Alias: "alias-b"},
				},
			},
			{
				APIKey: "low-key",
				Models: []internalconfig.GeminiModel{
					{Name: "upstream-shared", Alias: "alias-b"},
				},
			},
		},
	})

	decision, errDispatch = manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != low.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s after config reset and upstream cooldown", decision, low.ID)
	}
	if decision.UpstreamModel != "upstream-shared" {
		t.Fatalf("Dispatch(alias-b) upstream = %q, want upstream-shared", decision.UpstreamModel)
	}
}

func TestDispatchFastPathKeepsUpstreamCooldownPerAuth(t *testing.T) {
	manager := NewManager(nil, nil, nil)
	setGeminiAliasConfig(manager)
	high := geminiAPIKeyAuth("upstream-isolated-high", "high-key", "10")
	other := geminiAPIKeyAuth("upstream-isolated-other", "other-key", "1")
	registerDispatchTestAuth(t, manager, high, "alias-b")
	registerDispatchTestAuth(t, manager, other, "alias-b")

	markQuota429(t, manager, high.ID, "upstream-shared")

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != other.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s because it resolves alias-b to upstream-other", decision, other.ID)
	}
	if decision.UpstreamModel != "upstream-other" {
		t.Fatalf("Dispatch(alias-b) upstream = %q, want upstream-other", decision.UpstreamModel)
	}
}

func TestDispatchFastPathSkipsBlockedFullAuth(t *testing.T) {
	manager := NewManager(nil, nil, nil)
	setGeminiAliasConfig(manager)
	high := geminiAPIKeyAuth("upstream-full-blocked-high", "high-key", "10")
	low := geminiAPIKeyAuth("upstream-full-blocked-low", "low-key", "1")
	registerDispatchTestAuth(t, manager, high, "alias-b")
	registerDispatchTestAuth(t, manager, low, "alias-b")

	highFull := high.Clone()
	next := time.Now().Add(time.Hour)
	highFull.ModelStates = map[string]*ModelState{
		"upstream-shared": {
			Status:         StatusError,
			Unavailable:    true,
			NextRetryAfter: next,
			Quota: QuotaState{
				Exceeded:      true,
				NextRecoverAt: next,
			},
		},
	}
	manager.SetFullAuthResolver(dispatchTestFullAuthResolver{
		auths: map[string]*Auth{
			high.ID: highFull,
			low.ID:  low,
		},
	})

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != low.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s because full high auth is upstream blocked", decision, low.ID)
	}
	if decision.UpstreamModel != "upstream-shared" {
		t.Fatalf("Dispatch(alias-b) upstream = %q, want upstream-shared", decision.UpstreamModel)
	}
}

func TestDispatchFallbackSelectorSkipsUpstreamBlockedAuth(t *testing.T) {
	manager := NewManager(nil, firstCandidateSelector{}, nil)
	setGeminiAliasConfig(manager)
	high := geminiAPIKeyAuth("upstream-custom-high", "high-key", "10")
	low := geminiAPIKeyAuth("upstream-custom-low", "low-key", "1")
	registerDispatchTestAuth(t, manager, high, "alias-a", "alias-b")
	registerDispatchTestAuth(t, manager, low, "alias-a", "alias-b")
	markQuota429(t, manager, high.ID, "upstream-shared")

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != low.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s", decision, low.ID)
	}
}

func TestDispatchFallbackSelectorSkipsBlockedFullAuth(t *testing.T) {
	high := geminiAPIKeyAuth("upstream-fallback-full-blocked-high", "high-key", "10")
	low := geminiAPIKeyAuth("upstream-fallback-full-blocked-low", "low-key", "1")
	manager := NewManager(nil, orderedCandidateSelector{order: []string{high.ID, low.ID}}, nil)
	setGeminiAliasConfig(manager)
	registerDispatchTestAuth(t, manager, high, "alias-b")
	registerDispatchTestAuth(t, manager, low, "alias-b")

	highFull := high.Clone()
	next := time.Now().Add(time.Hour)
	highFull.ModelStates = map[string]*ModelState{
		"upstream-shared": {
			Status:         StatusError,
			Unavailable:    true,
			NextRetryAfter: next,
			Quota: QuotaState{
				Exceeded:      true,
				NextRecoverAt: next,
			},
		},
	}
	lowFull := low.Clone()
	manager.SetFullAuthResolver(dispatchTestFullAuthResolver{
		auths: map[string]*Auth{
			high.ID: highFull,
			low.ID:  lowFull,
		},
	})

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != low.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s because full high auth is upstream blocked", decision, low.ID)
	}
	if decision.UpstreamModel != "upstream-shared" {
		t.Fatalf("Dispatch(alias-b) upstream = %q, want upstream-shared", decision.UpstreamModel)
	}
}

func TestDispatchFallbackSelectorResolvesUpstreamFromFullAuth(t *testing.T) {
	manager := NewManager(nil, firstCandidateSelector{}, nil)
	setGeminiAliasConfig(manager)
	minimal := geminiAPIKeyAuth("upstream-fullauth", "high-key", "1")
	full := geminiAPIKeyAuth(minimal.ID, "other-key", "1")
	registerDispatchTestAuth(t, manager, minimal, "alias-b")
	manager.SetFullAuthResolver(dispatchTestFullAuthResolver{
		auths: map[string]*Auth{
			minimal.ID: full,
		},
	})

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != minimal.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s", decision, minimal.ID)
	}
	if decision.UpstreamModel != "upstream-other" {
		t.Fatalf("Dispatch(alias-b) upstream = %q, want upstream-other from full auth", decision.UpstreamModel)
	}
}

func TestDispatchKeepsClientSupportsModelOnRouteAlias(t *testing.T) {
	manager := NewManager(nil, nil, nil)
	setGeminiAliasConfig(manager)
	auth := geminiAPIKeyAuth("upstream-route-support", "high-key", "1")
	registerDispatchTestAuth(t, manager, auth, "alias-a")

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-a", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-a) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != auth.ID {
		t.Fatalf("Dispatch(alias-a) auth = %#v, want %s", decision, auth.ID)
	}

	_, errDispatch = manager.Dispatch(context.Background(), []string{"gemini"}, "upstream-shared", Options{})
	if errDispatch == nil {
		t.Fatal("Dispatch(upstream-shared) error = nil, want route model support check to reject non-registered upstream")
	}
}

func TestMarkResultStoresCanonicalUpstreamKey(t *testing.T) {
	manager := NewManager(nil, nil, nil)
	auth := geminiAPIKeyAuth("upstream-result-key", "high-key", "1")
	registerDispatchTestAuth(t, manager, auth, "alias-a")

	manager.MarkResult(context.Background(), Result{
		AuthID:  auth.ID,
		Model:   "upstream-shared(high)",
		Success: false,
		Error: &Error{
			Message:    "quota exhausted",
			HTTPStatus: http.StatusTooManyRequests,
		},
	})

	got, ok := manager.GetByID(auth.ID)
	if !ok || got == nil {
		t.Fatal("GetByID() missing auth")
	}
	if _, exists := got.ModelStates["upstream-shared"]; !exists {
		t.Fatalf("ModelStates keys = %#v, want canonical upstream-shared", got.ModelStates)
	}
	if _, exists := got.ModelStates["upstream-shared(high)"]; exists {
		t.Fatalf("ModelStates contains non-canonical key upstream-shared(high): %#v", got.ModelStates)
	}
}

func TestDispatchUsesLegacyRouteStateAsCompatibilityFallback(t *testing.T) {
	manager := NewManager(nil, nil, nil)
	setGeminiAliasConfig(manager)
	high := geminiAPIKeyAuth("upstream-legacy-high", "high-key", "10")
	low := geminiAPIKeyAuth("upstream-legacy-low", "low-key", "1")
	next := time.Now().Add(time.Minute)
	high.ModelStates = map[string]*ModelState{
		"alias-b": {
			Status:         StatusError,
			Unavailable:    true,
			NextRetryAfter: next,
			Quota: QuotaState{
				Exceeded:      true,
				NextRecoverAt: next,
			},
		},
	}
	registerDispatchTestAuth(t, manager, high, "alias-b")
	registerDispatchTestAuth(t, manager, low, "alias-b")

	decision, errDispatch := manager.Dispatch(context.Background(), []string{"gemini"}, "alias-b", Options{})
	if errDispatch != nil {
		t.Fatalf("Dispatch(alias-b) error = %v", errDispatch)
	}
	if decision == nil || decision.Auth == nil || decision.Auth.ID != low.ID {
		t.Fatalf("Dispatch(alias-b) auth = %#v, want %s because legacy route state still blocks high auth", decision, low.ID)
	}
}
