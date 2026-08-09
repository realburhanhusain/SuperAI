package management

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	coreauth "github.com/router-for-me/CLIProxyAPIHome/internal/cliproxy/auth"
	appconfig "github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/home"
)

func sumRecentRequestBuckets(buckets []coreauth.RecentRequestBucket) (int64, int64) {
	var success int64
	var failed int64
	for _, bucket := range buckets {
		success += bucket.Success
		failed += bucket.Failed
	}
	return success, failed
}

func TestGetAPIKeyUsageUsesHomeRuntimeAuths(t *testing.T) {
	rt, errRuntime := home.NewRuntime(&appconfig.Config{AuthDir: t.TempDir()})
	if errRuntime != nil {
		t.Fatalf("home.NewRuntime() error = %v", errRuntime)
	}
	manager := rt.CoreManager()
	if manager == nil {
		t.Fatal("CoreManager() = nil")
	}
	if _, errRegister := manager.Register(context.Background(), &coreauth.Auth{
		ID:       "vast-auth",
		Index:    "vast-auth",
		Provider: "openai-compatible-vast",
		Attributes: map[string]string{
			"api_key":     "vast-key",
			"base_url":    "https://www.vastnum.com/v1",
			"compat_name": "VAST",
		},
	}); errRegister != nil {
		t.Fatalf("Register() error = %v", errRegister)
	}

	if _, errRegister := manager.Register(context.Background(), &coreauth.Auth{
		ID:       "xai-api-key-auth",
		Index:    "xai-api-key-auth",
		Provider: "xai",
		Attributes: map[string]string{
			"api_key":  "xai-key",
			"base_url": "https://api.x.ai/v1",
		},
	}); errRegister != nil {
		t.Fatalf("Register(xAI) error = %v", errRegister)
	}

	manager.MarkResult(context.Background(), coreauth.Result{AuthID: "vast-auth", Provider: "openai-compatible-vast", Model: "gpt-5", Success: true})
	manager.MarkResult(context.Background(), coreauth.Result{AuthID: "vast-auth", Provider: "openai-compatible-vast", Model: "gpt-5", Success: false})
	manager.MarkResult(context.Background(), coreauth.Result{AuthID: "xai-api-key-auth", Provider: "xai", Model: "grok-4.5", Success: true})

	handler := NewHandler(nil, rt, "127.0.0.1", 0)
	rec := httptest.NewRecorder()
	ginCtx, _ := gin.CreateTestContext(rec)
	ginCtx.Request = httptest.NewRequest(http.MethodGet, "/v0/management/api-key-usage", nil)

	handler.GetAPIKeyUsage(ginCtx)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d body=%s", rec.Code, http.StatusOK, rec.Body.String())
	}

	var payload map[string]map[string]apiKeyUsageEntry
	if errDecode := json.Unmarshal(rec.Body.Bytes(), &payload); errDecode != nil {
		t.Fatalf("json.Unmarshal() error = %v", errDecode)
	}
	if _, exists := payload["openai-compatible-vast"]; exists {
		t.Fatalf("unexpected namespaced provider bucket: %#v", payload)
	}
	vastBucket, exists := payload["vast"]
	if !exists {
		t.Fatalf("missing compat provider bucket: %#v", payload)
	}
	entry := vastBucket["https://www.vastnum.com/v1|vast-key"]
	if entry.Success != 1 || entry.Failed != 1 {
		t.Fatalf("totals = %d/%d, want 1/1", entry.Success, entry.Failed)
	}
	if len(entry.RecentRequests) != 20 {
		t.Fatalf("recent request bucket count = %d, want 20", len(entry.RecentRequests))
	}
	success, failed := sumRecentRequestBuckets(entry.RecentRequests)
	if success != 1 || failed != 1 {
		t.Fatalf("recent request totals = %d/%d, want 1/1", success, failed)
	}

	xaiBucket, exists := payload["xai"]
	if !exists {
		t.Fatalf("missing xAI provider bucket: %#v", payload)
	}
	xaiEntry := xaiBucket["https://api.x.ai/v1|xai-key"]
	if xaiEntry.Success != 1 || xaiEntry.Failed != 0 {
		t.Fatalf("xAI totals = %d/%d, want 1/0", xaiEntry.Success, xaiEntry.Failed)
	}
	xaiSuccess, xaiFailed := sumRecentRequestBuckets(xaiEntry.RecentRequests)
	if xaiSuccess != 1 || xaiFailed != 0 {
		t.Fatalf("xAI recent request totals = %d/%d, want 1/0", xaiSuccess, xaiFailed)
	}
}
