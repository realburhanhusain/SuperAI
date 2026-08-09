package get

import (
	"context"
	"encoding/json"
	"path/filepath"
	"testing"
	"time"

	"github.com/router-for-me/CLIProxyAPI/v7/sdk/pluginstore"
	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/home"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

func TestHandlePluginSyncRequiresActiveMTLSNode(t *testing.T) {
	runtime := pluginSyncTestRuntime(t)
	request, _ := json.Marshal(pluginstore.PluginSyncRequest{
		SchemaVersion: pluginstore.PluginSyncSchemaVersion, GOOS: "linux", GOARCH: "amd64",
	})
	missing := handlePluginSync(context.Background(), dispatch.Env{Runtime: runtime}, []string{"GET", "plugin-sync", string(request)})
	if missing.Kind != dispatch.ReplyKindRedisError {
		t.Fatalf("missing identity reply = %#v", missing)
	}
	runtime.SetPluginSyncNodeActive(func(context.Context, string, string) (bool, error) { return false, nil })
	revoked := handlePluginSync(context.Background(), dispatch.Env{Runtime: runtime, NodeID: "node-1", ClientCertificateFingerprint: "fingerprint"}, []string{"GET", "plugin-sync", string(request)})
	if revoked.Kind != dispatch.ReplyKindRedisError {
		t.Fatalf("revoked identity reply = %#v", revoked)
	}
	runtime.SetPluginSyncNodeActive(func(context.Context, string, string) (bool, error) { return true, nil })
	active := handlePluginSync(context.Background(), dispatch.Env{Runtime: runtime, NodeID: "node-1", ClientCertificateFingerprint: "fingerprint"}, []string{"GET", "plugin-sync", string(request)})
	if active.Kind != dispatch.ReplyKindBulkString || !active.Sensitive {
		t.Fatalf("active identity reply = %#v, want sensitive bulk string", active)
	}
	var response pluginstore.PluginSyncResponse
	if errDecode := json.Unmarshal(active.BulkString, &response); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	defer response.Clear()
	if response.SchemaVersion != pluginstore.PluginSyncSchemaVersion || len(response.Items) != 0 {
		t.Fatalf("response = %#v, want empty valid plan", response)
	}
}

func TestMarshalPluginSyncResponseUsesOneClearableBacking(t *testing.T) {
	response := pluginstore.PluginSyncResponse{
		SchemaVersion: pluginstore.PluginSyncSchemaVersion,
		ExpiresAt:     time.Now().UTC().Add(time.Minute),
		Items: []pluginstore.PluginSyncItem{{
			Manifest: pluginstore.Manifest{
				SchemaVersion: 2,
				ID:            "sample",
				Version:       "1.0.0",
				Install: pluginstore.InstallPlan{Type: pluginstore.InstallTypeDirect, Artifacts: []pluginstore.Artifact{{
					GOOS: "linux", GOARCH: "amd64", URL: "https://downloads.example/sample.zip",
					SHA256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
				}}},
			},
			Auth: []pluginstore.ResolvedAuthConfig{
				{Match: "https://downloads.example/", Type: pluginstore.AuthTypeBearer, Token: pluginstore.Secret("token-secret")},
				{Match: "https://downloads.example/", Type: pluginstore.AuthTypeBasic, Username: pluginstore.Secret("user-secret"), Password: pluginstore.Secret("password-secret")},
				{Match: "https://downloads.example/", Type: pluginstore.AuthTypeHeader, HeaderName: "X-Plugin-Token", HeaderValue: pluginstore.Secret("header-secret")},
			},
		}},
	}
	defer response.Clear()
	raw, errMarshal := marshalPluginSyncResponse(response)
	if errMarshal != nil {
		t.Fatalf("marshalPluginSyncResponse() error = %v", errMarshal)
	}
	if len(raw) != cap(raw) {
		clearPluginSyncJSON(raw)
		t.Fatalf("JSON len/cap = %d/%d, want one exact backing", len(raw), cap(raw))
	}
	backing := raw
	var decoded pluginstore.PluginSyncResponse
	if errDecode := json.Unmarshal(raw, &decoded); errDecode != nil {
		clearPluginSyncJSON(raw)
		t.Fatalf("decode response: %v", errDecode)
	}
	defer decoded.Clear()
	if len(decoded.Items) != 1 || len(decoded.Items[0].Auth) != 3 || string(decoded.Items[0].Auth[0].Token) != "token-secret" ||
		string(decoded.Items[0].Auth[1].Password) != "password-secret" || string(decoded.Items[0].Auth[2].HeaderValue) != "header-secret" {
		clearPluginSyncJSON(raw)
		t.Fatalf("decoded response = %#v", decoded)
	}
	clearPluginSyncJSON(raw)
	for index, value := range backing {
		if value != 0 {
			t.Fatalf("JSON byte %d = %d, want zero", index, value)
		}
	}
}

func TestMarshalPluginSyncResponseEscapesControlCharactersAsJSON(t *testing.T) {
	response := pluginstore.PluginSyncResponse{
		SchemaVersion: pluginstore.PluginSyncSchemaVersion,
		ExpiresAt:     time.Now().UTC().Add(time.Minute),
		Items: []pluginstore.PluginSyncItem{{Auth: []pluginstore.ResolvedAuthConfig{{
			Match: "https://downloads.example/", Type: pluginstore.AuthTypeHeader,
			HeaderName: "X\x01Y", HeaderValue: pluginstore.Secret("secret"),
		}}}},
	}
	defer response.Clear()
	raw, errMarshal := marshalPluginSyncResponse(response)
	if errMarshal != nil {
		t.Fatalf("marshalPluginSyncResponse() error = %v", errMarshal)
	}
	defer clearPluginSyncJSON(raw)
	if !json.Valid(raw) {
		t.Fatalf("marshalPluginSyncResponse() emitted invalid JSON: %q", raw)
	}
}

func pluginSyncTestRuntime(t *testing.T) *home.Runtime {
	t.Helper()
	cfg := &config.Config{AuthDir: filepath.Join(t.TempDir(), "auths")}
	runtime, errRuntime := home.NewRuntime(cfg)
	if errRuntime != nil {
		t.Fatalf("NewRuntime() error = %v", errRuntime)
	}
	t.Cleanup(runtime.Stop)
	return runtime
}
