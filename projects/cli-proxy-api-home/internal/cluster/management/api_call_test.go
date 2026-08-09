package management

import (
	"net/http"
	"testing"

	coreauth "github.com/router-for-me/CLIProxyAPIHome/internal/cliproxy/auth"
)

func TestAPICallAuthMatchesOAuthFileName(t *testing.T) {
	t.Parallel()

	auth := &coreauth.Auth{
		ID:       "7f2f0f1d-40d1-4f9a-9045-4b83412c8188",
		Index:    "7f2f0f1d-40d1-4f9a-9045-4b83412c8188",
		Provider: "codex",
		Label:    "codex-user",
		Metadata: map[string]any{
			"type":     "codex",
			"filename": "codex-user.json",
		},
	}

	for _, selector := range []string{
		auth.ID,
		auth.Index,
		"codex-user.json",
		"codex-user",
	} {
		selector := selector
		t.Run(selector, func(t *testing.T) {
			t.Parallel()

			if !apiCallAuthMatches(auth.Clone(), selector) {
				t.Fatalf("apiCallAuthMatches returned false for selector %q", selector)
			}
		})
	}
}

func TestAPICallTransportUsesOAuthMetadataProxyURL(t *testing.T) {
	t.Parallel()

	auth := &coreauth.Auth{
		ID:       "codex-auth",
		Provider: "codex",
		Metadata: map[string]any{
			"type":      "codex",
			"proxy_url": "http://codex-proxy.example.com:8080",
		},
	}
	transport := (&Handler{}).apiCallTransport(auth)
	httpTransport, ok := transport.(*http.Transport)
	if !ok {
		t.Fatalf("transport type = %T, want *http.Transport", transport)
	}

	req, errRequest := http.NewRequest(http.MethodGet, "https://example.com", nil)
	if errRequest != nil {
		t.Fatalf("http.NewRequest returned error: %v", errRequest)
	}
	proxyURL, errProxy := httpTransport.Proxy(req)
	if errProxy != nil {
		t.Fatalf("httpTransport.Proxy returned error: %v", errProxy)
	}
	if proxyURL == nil || proxyURL.String() != "http://codex-proxy.example.com:8080" {
		t.Fatalf("proxy URL = %v, want http://codex-proxy.example.com:8080", proxyURL)
	}
}
