package management

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestPluginAuthProviderFromManagementPath(t *testing.T) {
	tests := []struct {
		name     string
		path     string
		provider string
		ok       bool
	}{
		{name: "valid", path: "/v0/management/gemini-cli-auth-url", provider: "gemini-cli", ok: true},
		{name: "upper normalized", path: "/v0/management/Gemini-auth-url", provider: "gemini", ok: true},
		{name: "underscore rejected", path: "/v0/management/gemini_cli-auth-url", ok: false},
		{name: "wrong suffix", path: "/v0/management/gemini-cli-auth", ok: false},
		{name: "wrong prefix", path: "/v0/other/gemini-cli-auth-url", ok: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			provider, ok := pluginAuthProviderFromManagementPath(tt.path)
			if ok != tt.ok || provider != tt.provider {
				t.Fatalf("pluginAuthProviderFromManagementPath(%q) = %q, %t; want %q, %t", tt.path, provider, ok, tt.provider, tt.ok)
			}
		})
	}
}

func TestPluginOAuthPollMetadataOmitsSessionSource(t *testing.T) {
	data := pluginOAuthSessionData(map[string]any{
		"poll_token": "token-1",
	})
	data["callback_code"] = "code-1"

	if !oauthSessionIsPlugin(data) {
		t.Fatal("oauthSessionIsPlugin() = false, want true")
	}
	pollMetadata := pluginOAuthPollMetadata(data)
	if _, exists := pollMetadata["source"]; exists {
		t.Fatalf("poll metadata contains source: %#v", pollMetadata)
	}
	if pollMetadata["poll_token"] != "token-1" || pollMetadata["callback_code"] != "code-1" {
		t.Fatalf("poll metadata = %#v, want plugin metadata and callback code", pollMetadata)
	}
}

func TestPluginManagementCallbackURLUsesForwardedHeaders(t *testing.T) {
	gin.SetMode(gin.TestMode)
	recorder := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(recorder)
	req := httptest.NewRequest(http.MethodGet, "http://internal.example/v0/management/gemini-cli-auth-url", nil)
	req.Header.Set("X-Forwarded-Proto", "https")
	req.Header.Set("X-Forwarded-Host", "home.example.test")
	c.Request = req

	handler := NewHandler(nil, nil, "127.0.0.1", 8317)
	got, errURL := handler.pluginManagementCallbackURL(c, "/v0/management/oauth-callback")
	if errURL != nil {
		t.Fatalf("pluginManagementCallbackURL() error = %v", errURL)
	}
	if want := "https://home.example.test/v0/management/oauth-callback"; got != want {
		t.Fatalf("pluginManagementCallbackURL() = %q, want %q", got, want)
	}
}
