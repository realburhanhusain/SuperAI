package management

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
)

func TestProxyPoolCreateListUpdateDeleteHandlers(t *testing.T) {
	t.Parallel()

	handler, closeRepo := newBillingManagementTestHandler(t)
	defer closeRepo()

	createResp := httptest.NewRecorder()
	createCtx, _ := gin.CreateTestContext(createResp)
	createCtx.Request = httptest.NewRequest(http.MethodPost, "/proxy/proxy-pools", bytes.NewReader([]byte(`{"name":"Primary proxy","proxy_url":"http://127.0.0.1:18080","enabled":true,"priority":20,"note":"initial"}`)))
	createCtx.Request.Header.Set("Content-Type", "application/json")

	handler.CreateProxyPoolItem(createCtx)

	if createResp.Code != http.StatusOK {
		t.Fatalf("create status = %d body=%s, want 200", createResp.Code, createResp.Body.String())
	}
	var createPayload map[string]any
	if errDecode := json.Unmarshal(createResp.Body.Bytes(), &createPayload); errDecode != nil {
		t.Fatalf("decode create response: %v", errDecode)
	}
	proxyPool, ok := createPayload["proxy_pool"].(map[string]any)
	if !ok {
		t.Fatalf("proxy_pool = %T, want object", createPayload["proxy_pool"])
	}
	id, ok := proxyPool["id"].(string)
	if !ok || id == "" {
		t.Fatalf("proxy_pool.id = %v, want non-empty string", proxyPool["id"])
	}
	if proxyPool["last_test_result"] != cluster.ProxyPoolTestResultUntested {
		t.Fatalf("last_test_result = %v, want untested", proxyPool["last_test_result"])
	}

	updateResp := httptest.NewRecorder()
	updateCtx, _ := gin.CreateTestContext(updateResp)
	updateCtx.Params = gin.Params{{Key: "id", Value: id}}
	updateCtx.Request = httptest.NewRequest(http.MethodPatch, "/proxy/proxy-pools/"+id, bytes.NewReader([]byte(`{"name":"Primary proxy updated","proxy_url":"https://127.0.0.1:18081","enabled":false,"scope":"global","priority":5,"note":"updated"}`)))
	updateCtx.Request.Header.Set("Content-Type", "application/json")

	handler.UpdateProxyPoolItem(updateCtx)

	if updateResp.Code != http.StatusOK {
		t.Fatalf("update status = %d body=%s, want 200", updateResp.Code, updateResp.Body.String())
	}

	listResp := httptest.NewRecorder()
	listCtx, _ := gin.CreateTestContext(listResp)
	listCtx.Request = httptest.NewRequest(http.MethodGet, "/proxy/proxy-pools", nil)

	handler.ListProxyPoolItems(listCtx)

	if listResp.Code != http.StatusOK {
		t.Fatalf("list status = %d body=%s, want 200", listResp.Code, listResp.Body.String())
	}
	var listPayload map[string]any
	if errDecode := json.Unmarshal(listResp.Body.Bytes(), &listPayload); errDecode != nil {
		t.Fatalf("decode list response: %v", errDecode)
	}
	items, ok := listPayload["items"].([]any)
	if !ok {
		t.Fatalf("items = %T, want array", listPayload["items"])
	}
	if len(items) != 1 {
		t.Fatalf("item count = %d, want 1", len(items))
	}
	item, ok := items[0].(map[string]any)
	if !ok {
		t.Fatalf("item = %T, want object", items[0])
	}
	if item["name"] != "Primary proxy updated" || item["enabled"] != false || item["priority"] != float64(5) {
		t.Fatalf("listed item = %#v, want updated fields", item)
	}

	deleteResp := httptest.NewRecorder()
	deleteCtx, _ := gin.CreateTestContext(deleteResp)
	deleteCtx.Params = gin.Params{{Key: "id", Value: id}}
	deleteCtx.Request = httptest.NewRequest(http.MethodDelete, "/proxy/proxy-pools/"+id, nil)

	handler.DeleteProxyPoolItem(deleteCtx)

	if deleteResp.Code != http.StatusOK {
		t.Fatalf("delete status = %d body=%s, want 200", deleteResp.Code, deleteResp.Body.String())
	}
	records, errList := handler.repo.ListProxyPoolItems(context.Background())
	if errList != nil {
		t.Fatalf("ListProxyPoolItems() error = %v", errList)
	}
	if len(records) != 0 {
		t.Fatalf("record count after delete = %d, want 0", len(records))
	}
}

func TestProxyPoolCreateOmittedEnabledDefaultsTrue(t *testing.T) {
	t.Parallel()

	handler, closeRepo := newBillingManagementTestHandler(t)
	defer closeRepo()

	resp := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(resp)
	ctx.Request = httptest.NewRequest(http.MethodPost, "/proxy/proxy-pools", bytes.NewReader([]byte(`{"name":"Default enabled proxy","proxy_url":"http://127.0.0.1:18080","priority":10}`)))
	ctx.Request.Header.Set("Content-Type", "application/json")

	handler.CreateProxyPoolItem(ctx)

	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s, want 200", resp.Code, resp.Body.String())
	}
	var payload map[string]any
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &payload); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	proxyPool, ok := payload["proxy_pool"].(map[string]any)
	if !ok {
		t.Fatalf("proxy_pool = %T, want object", payload["proxy_pool"])
	}
	if proxyPool["enabled"] != true {
		t.Fatalf("proxy_pool.enabled = %v, want true", proxyPool["enabled"])
	}
	id, ok := proxyPool["id"].(string)
	if !ok || id == "" {
		t.Fatalf("proxy_pool.id = %v, want non-empty string", proxyPool["id"])
	}
	stored, errGet := handler.repo.GetProxyPoolItem(context.Background(), id)
	if errGet != nil {
		t.Fatalf("GetProxyPoolItem() error = %v", errGet)
	}
	if !stored.Enabled {
		t.Fatal("stored Enabled = false, want true")
	}
}

func TestProxyPoolPatchEnabledPreservesExistingFields(t *testing.T) {
	t.Parallel()

	handler, closeRepo := newBillingManagementTestHandler(t)
	defer closeRepo()

	record, errCreate := handler.repo.CreateProxyPoolItem(context.Background(), cluster.ProxyPoolUpdate{
		Name:     "Patch proxy",
		ProxyURL: "http://127.0.0.1:18080",
		Enabled:  boolPtr(true),
		Scope:    cluster.ProxyPoolScopeGlobal,
		Priority: 30,
		Note:     "keep note",
	})
	if errCreate != nil {
		t.Fatalf("CreateProxyPoolItem() error = %v", errCreate)
	}

	resp := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(resp)
	ctx.Params = gin.Params{{Key: "id", Value: record.ID}}
	ctx.Request = httptest.NewRequest(http.MethodPatch, "/proxy/proxy-pools/"+record.ID, bytes.NewReader([]byte(`{"enabled":false}`)))
	ctx.Request.Header.Set("Content-Type", "application/json")

	handler.UpdateProxyPoolItem(ctx)

	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s, want 200", resp.Code, resp.Body.String())
	}
	var payload map[string]any
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &payload); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	proxyPool, ok := payload["proxy_pool"].(map[string]any)
	if !ok {
		t.Fatalf("proxy_pool = %T, want object", payload["proxy_pool"])
	}
	if proxyPool["enabled"] != false {
		t.Fatalf("proxy_pool.enabled = %v, want false", proxyPool["enabled"])
	}
	if proxyPool["name"] != record.Name || proxyPool["proxy_url"] != record.ProxyURL || proxyPool["scope"] != record.Scope || proxyPool["priority"] != float64(record.Priority) || proxyPool["note"] != record.Note {
		t.Fatalf("proxy_pool = %#v, want unspecified fields preserved", proxyPool)
	}

	stored, errGet := handler.repo.GetProxyPoolItem(context.Background(), record.ID)
	if errGet != nil {
		t.Fatalf("GetProxyPoolItem() error = %v", errGet)
	}
	if stored.Enabled || stored.Name != record.Name || stored.ProxyURL != record.ProxyURL || stored.Priority != record.Priority || stored.Note != record.Note || stored.Scope != record.Scope {
		t.Fatalf("stored record = %#v, want enabled false with other fields preserved", stored)
	}
}

func TestProxyPoolInvalidCreateBodyAndScopeReturnBadRequest(t *testing.T) {
	t.Parallel()

	handler, closeRepo := newBillingManagementTestHandler(t)
	defer closeRepo()

	tests := []struct {
		name string
		body string
	}{
		{name: "invalid body", body: `{`},
		{name: "invalid scope", body: `{"name":"Team proxy","proxy_url":"http://127.0.0.1:18080","scope":"team"}`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			resp := httptest.NewRecorder()
			ctx, _ := gin.CreateTestContext(resp)
			ctx.Request = httptest.NewRequest(http.MethodPost, "/proxy/proxy-pools", bytes.NewReader([]byte(tt.body)))
			ctx.Request.Header.Set("Content-Type", "application/json")

			handler.CreateProxyPoolItem(ctx)

			if resp.Code != http.StatusBadRequest {
				t.Fatalf("status = %d body=%s, want 400", resp.Code, resp.Body.String())
			}
		})
	}
}

func TestProxyPoolTestMissingItemReturnsNotFound(t *testing.T) {
	t.Parallel()

	handler, closeRepo := newBillingManagementTestHandler(t)
	defer closeRepo()

	resp := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(resp)
	ctx.Params = gin.Params{{Key: "id", Value: "proxy_missing"}}
	ctx.Request = httptest.NewRequest(http.MethodPost, "/proxy/proxy-pools/proxy_missing/test", nil)

	handler.TestProxyPoolItem(ctx)

	if resp.Code != http.StatusNotFound {
		t.Fatalf("status = %d body=%s, want 404", resp.Code, resp.Body.String())
	}
	var payload map[string]any
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &payload); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if payload["error"] != "proxy_pool_not_found" {
		t.Fatalf("error = %v, want proxy_pool_not_found", payload["error"])
	}
}

func TestProxyPoolTestFailingProxyPersistsFailedResult(t *testing.T) {
	t.Parallel()

	handler, closeRepo := newBillingManagementTestHandler(t)
	defer closeRepo()

	failingProxy := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "proxy unavailable", http.StatusBadGateway)
	}))
	defer failingProxy.Close()

	record, errCreate := handler.repo.CreateProxyPoolItem(context.Background(), cluster.ProxyPoolUpdate{
		Name:     "Failing proxy",
		ProxyURL: failingProxy.URL,
		Enabled:  boolPtr(true),
	})
	if errCreate != nil {
		t.Fatalf("CreateProxyPoolItem() error = %v", errCreate)
	}

	resp := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(resp)
	ctx.Params = gin.Params{{Key: "id", Value: record.ID}}
	ctx.Request = httptest.NewRequest(http.MethodPost, fmt.Sprintf("/proxy/proxy-pools/%s/test", record.ID), nil)

	handler.TestProxyPoolItem(ctx)

	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s, want 200", resp.Code, resp.Body.String())
	}
	var payload map[string]any
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &payload); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if payload["result"] != cluster.ProxyPoolTestResultFailed {
		t.Fatalf("result = %v, want failed", payload["result"])
	}
	updated, errGet := handler.repo.GetProxyPoolItem(context.Background(), record.ID)
	if errGet != nil {
		t.Fatalf("GetProxyPoolItem() error = %v", errGet)
	}
	if updated.LastTestResult != cluster.ProxyPoolTestResultFailed {
		t.Fatalf("persisted last_test_result = %q, want failed", updated.LastTestResult)
	}
	if updated.LastTestedAt == nil {
		t.Fatal("persisted last_tested_at is nil")
	}
}

func boolPtr(value bool) *bool {
	return &value
}
