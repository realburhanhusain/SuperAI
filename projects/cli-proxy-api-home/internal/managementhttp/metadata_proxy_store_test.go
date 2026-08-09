package managementhttp

import (
	"context"
	"testing"

	cpacoreauth "github.com/router-for-me/CLIProxyAPI/v7/sdk/cliproxy/auth"
)

type memoryMetadataProxyStore struct {
	items   []*cpacoreauth.Auth
	baseDir string
}

func (s *memoryMetadataProxyStore) List(context.Context) ([]*cpacoreauth.Auth, error) {
	return s.items, nil
}

func (s *memoryMetadataProxyStore) Save(context.Context, *cpacoreauth.Auth) (string, error) {
	return "", nil
}

func (s *memoryMetadataProxyStore) Delete(context.Context, string) error {
	return nil
}

func (s *memoryMetadataProxyStore) SetBaseDir(dir string) {
	s.baseDir = dir
}

func TestMetadataProxyStoreBackfillsProxyURLFromMetadata(t *testing.T) {
	t.Parallel()

	inner := &memoryMetadataProxyStore{
		items: []*cpacoreauth.Auth{{
			ID: "codex-auth",
			Metadata: map[string]any{
				"proxy_url": " http://auth-proxy.example.com:8080 ",
			},
		}},
	}
	store := newMetadataProxyStore(inner)

	items, errList := store.List(context.Background())
	if errList != nil {
		t.Fatalf("List returned error: %v", errList)
	}
	if len(items) != 1 {
		t.Fatalf("List returned %d items, want 1", len(items))
	}
	if items[0].ProxyURL != "http://auth-proxy.example.com:8080" {
		t.Fatalf("ProxyURL = %q, want metadata proxy URL", items[0].ProxyURL)
	}
}

func TestMetadataProxyStoreKeepsExplicitProxyURL(t *testing.T) {
	t.Parallel()

	inner := &memoryMetadataProxyStore{
		items: []*cpacoreauth.Auth{{
			ID:       "codex-auth",
			ProxyURL: "http://explicit-proxy.example.com:8080",
			Metadata: map[string]any{
				"proxy_url": "http://metadata-proxy.example.com:8080",
			},
		}},
	}
	store := newMetadataProxyStore(inner)

	items, errList := store.List(context.Background())
	if errList != nil {
		t.Fatalf("List returned error: %v", errList)
	}
	if items[0].ProxyURL != "http://explicit-proxy.example.com:8080" {
		t.Fatalf("ProxyURL = %q, want explicit proxy URL", items[0].ProxyURL)
	}
}

func TestMetadataProxyStoreDelegatesBaseDir(t *testing.T) {
	t.Parallel()

	inner := &memoryMetadataProxyStore{}
	store := newMetadataProxyStore(inner)
	setter, ok := store.(interface{ SetBaseDir(string) })
	if !ok {
		t.Fatal("metadata proxy store does not expose SetBaseDir")
	}
	setter.SetBaseDir("/tmp/auth")
	if inner.baseDir != "/tmp/auth" {
		t.Fatalf("baseDir = %q, want delegated value", inner.baseDir)
	}
}
