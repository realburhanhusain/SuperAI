package home

import (
	"context"
	"fmt"
	"net/http"

	"github.com/router-for-me/CLIProxyAPIHome/internal/access"
)

const clusterAPIKeyAccessProviderName = "cluster-api-key"

type apiKeyValidator interface {
	ValidateAPIKey(ctx context.Context, apiKey string) (bool, error)
}

type clusterAPIKeyAccessProvider struct {
	validator apiKeyValidator
}

func newClusterAPIKeyAccessProvider(validator apiKeyValidator) *clusterAPIKeyAccessProvider {
	return &clusterAPIKeyAccessProvider{validator: validator}
}

func (p *clusterAPIKeyAccessProvider) Identifier() string {
	return clusterAPIKeyAccessProviderName
}

func (p *clusterAPIKeyAccessProvider) Authenticate(ctx context.Context, r *http.Request) (*access.Result, *access.AuthError) {
	if p == nil || p.validator == nil {
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
		valid, errValidate := p.validator.ValidateAPIKey(ctx, candidate.Value)
		if errValidate != nil {
			return nil, access.NewInternalAuthError("Authentication service error", fmt.Errorf("validate api key: %w", errValidate))
		}
		if valid {
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
