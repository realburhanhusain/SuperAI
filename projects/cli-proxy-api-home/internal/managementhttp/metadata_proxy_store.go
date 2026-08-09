package managementhttp

import (
	"context"
	"fmt"
	"strings"

	cpacoreauth "github.com/router-for-me/CLIProxyAPI/v7/sdk/cliproxy/auth"
)

type metadataProxyStore struct {
	inner cpacoreauth.Store
}

func newMetadataProxyStore(inner cpacoreauth.Store) cpacoreauth.Store {
	if inner == nil {
		return nil
	}
	return &metadataProxyStore{inner: inner}
}

func (s *metadataProxyStore) List(ctx context.Context) ([]*cpacoreauth.Auth, error) {
	if s == nil || s.inner == nil {
		return nil, nil
	}
	items, errList := s.inner.List(ctx)
	if errList != nil {
		return nil, errList
	}
	for _, auth := range items {
		applyMetadataProxyURL(auth)
	}
	return items, nil
}

func (s *metadataProxyStore) Save(ctx context.Context, auth *cpacoreauth.Auth) (string, error) {
	if s == nil || s.inner == nil {
		return "", fmt.Errorf("metadata proxy store: inner store unavailable")
	}
	return s.inner.Save(ctx, auth)
}

func (s *metadataProxyStore) Delete(ctx context.Context, id string) error {
	if s == nil || s.inner == nil {
		return fmt.Errorf("metadata proxy store: inner store unavailable")
	}
	return s.inner.Delete(ctx, id)
}

func (s *metadataProxyStore) SetBaseDir(dir string) {
	if s == nil || s.inner == nil {
		return
	}
	if setter, ok := s.inner.(interface{ SetBaseDir(string) }); ok {
		setter.SetBaseDir(dir)
	}
}

func applyMetadataProxyURL(auth *cpacoreauth.Auth) {
	if auth == nil || strings.TrimSpace(auth.ProxyURL) != "" || len(auth.Metadata) == 0 {
		return
	}
	for _, key := range []string{"proxy_url", "proxy-url"} {
		if proxyURL := metadataProxyString(auth.Metadata[key]); proxyURL != "" {
			auth.ProxyURL = proxyURL
			return
		}
	}
}

func metadataProxyString(raw any) string {
	switch value := raw.(type) {
	case string:
		return strings.TrimSpace(value)
	case fmt.Stringer:
		return strings.TrimSpace(value.String())
	default:
		return ""
	}
}
