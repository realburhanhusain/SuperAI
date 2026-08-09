package configaccess

import (
	"context"
	"net/http"
	"strings"

	"github.com/router-for-me/CLIProxyAPIHome/internal/access"
	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
)

// Register ensures the config-access provider is available to the access manager.
func Register(cfg *config.SDKConfig) {
	if cfg == nil {
		access.UnregisterProvider(access.AccessProviderTypeConfigAPIKey)
		return
	}

	keys := normalizeKeys(cfg.APIKeys)
	if len(keys) == 0 {
		access.UnregisterProvider(access.AccessProviderTypeConfigAPIKey)
		return
	}

	access.RegisterProvider(
		access.AccessProviderTypeConfigAPIKey,
		newProvider(access.DefaultAccessProviderName, keys),
	)
}

type provider struct {
	name string
	keys map[string]struct{}
}

// newProvider creates a provider.
func newProvider(name string, keys []string) *provider {
	providerName := strings.TrimSpace(name)
	if providerName == "" {
		providerName = access.DefaultAccessProviderName
	}
	keySet := make(map[string]struct{}, len(keys))
	for _, key := range keys {
		keySet[key] = struct{}{}
	}
	return &provider{name: providerName, keys: keySet}
}

// Identifier returns the provider identifier.
func (p *provider) Identifier() string {
	if p == nil || p.name == "" {
		return access.DefaultAccessProviderName
	}
	return p.name
}

// Authenticate validates request credentials and returns the access result.
func (p *provider) Authenticate(_ context.Context, r *http.Request) (*access.Result, *access.AuthError) {
	if p == nil {
		return nil, access.NewNotHandledError()
	}
	if len(p.keys) == 0 {
		return nil, access.NewNotHandledError()
	}
	candidates, ok := access.CredentialCandidatesFromRequest(r)
	if !ok {
		return nil, access.NewNoCredentialsError()
	}

	for _, candidate := range candidates {
		if candidate.Value == "" {
			continue
		}
		if _, ok := p.keys[candidate.Value]; ok {
			return &access.Result{
				Provider:  p.Identifier(),
				Principal: candidate.Value,
				Metadata: map[string]string{
					"source": candidate.Source,
				},
			}, nil
		}
	}

	return nil, access.NewInvalidCredentialError()
}

// normalizeKeys normalizes a keys.
func normalizeKeys(keys []string) []string {
	if len(keys) == 0 {
		return nil
	}
	normalized := make([]string, 0, len(keys))
	seen := make(map[string]struct{}, len(keys))
	for _, key := range keys {
		trimmedKey := strings.TrimSpace(key)
		if trimmedKey == "" {
			continue
		}
		if _, exists := seen[trimmedKey]; exists {
			continue
		}
		seen[trimmedKey] = struct{}{}
		normalized = append(normalized, trimmedKey)
	}
	if len(normalized) == 0 {
		return nil
	}
	return normalized
}
