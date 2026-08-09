package management

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPI/v7/sdk/pluginstore"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
	"github.com/router-for-me/CLIProxyAPIHome/internal/pluginauth"
)

func TestInstallPluginFromStoreWritesManifestConfig(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
			"dir":     t.TempDir(),
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(fakePluginStoreHTTPClient{
		pluginstore.DefaultRegistryURL: []byte(`{
			"schema_version": 1,
			"plugins": [{
				"id": "sample-provider",
				"name": "Sample Provider",
				"description": "Adds sample provider support.",
				"author": "author-name",
				"repository": "https://github.com/author-name/sample-provider"
			}]
		}`),
		"https://api.github.com/repos/author-name/sample-provider/releases/latest": []byte(`{
			"tag_name": "v0.2.0",
			"assets": []
		}`),
	})
	engine := gin.New()
	engine.POST("/plugin-store/:id/install", handler.InstallPluginFromStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}

	cfg, _, errConfig := repo.LoadConfigAsRuntimeConfig(context.Background())
	if errConfig != nil {
		t.Fatalf("LoadConfigAsRuntimeConfig() error = %v", errConfig)
	}
	item, okItem := cfg.Plugins.Configs["sample-provider"]
	if !okItem {
		t.Fatal("plugin config missing after install")
	}
	if item.Enabled == nil || !*item.Enabled {
		t.Fatalf("plugin enabled = %v, want true", item.Enabled)
	}
	storeNode := yamlMappingValue(&item.Raw, "store")
	if storeNode == nil {
		t.Fatal("plugin store manifest missing")
	}
	var manifest pluginstore.Manifest
	if errDecode := storeNode.Decode(&manifest); errDecode != nil {
		t.Fatalf("decode manifest: %v", errDecode)
	}
	if manifest.ID != "sample-provider" || manifest.Version != "0.2.0" || manifest.ReleaseTag != "v0.2.0" ||
		manifest.Repository != "https://github.com/author-name/sample-provider" || manifest.SourceID != pluginstore.DefaultSourceID {
		t.Fatalf("manifest = %+v, want pinned store metadata", manifest)
	}
}

func TestInstallPluginFromStoreHonorsQueryVersion(t *testing.T) {
	repo, engine := setupPluginStoreInstallTest(t, fakePluginStoreHTTPClient{
		"https://api.github.com/repos/author-name/sample-provider/releases/tags/v0.3.0": []byte(`{
			"tag_name": "v0.3.0",
			"assets": []
		}`),
	})

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install?version=0.3.0", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	assertPluginStoreInstallResponseVersion(t, resp, "0.3.0")
	assertInstalledPluginStoreManifest(t, repo, "sample-provider", "0.3.0", "v0.3.0")
}

func TestInstallPluginFromStoreHonorsUnprefixedReleaseTag(t *testing.T) {
	repo, engine := setupPluginStoreInstallTest(t, fakePluginStoreHTTPClient{
		"https://api.github.com/repos/author-name/sample-provider/releases/tags/0.5.0": []byte(`{
			"tag_name": "0.5.0",
			"assets": []
		}`),
	})

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install?version=0.5.0", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	assertPluginStoreInstallResponseVersion(t, resp, "0.5.0")
	assertInstalledPluginStoreManifest(t, repo, "sample-provider", "0.5.0", "0.5.0")
}

func TestInstallPluginFromStoreHonorsBodyVersion(t *testing.T) {
	repo, engine := setupPluginStoreInstallTest(t, fakePluginStoreHTTPClient{
		"https://api.github.com/repos/author-name/sample-provider/releases/tags/v0.4.0": []byte(`{
			"tag_name": "v0.4.0",
			"assets": []
		}`),
	})

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install", strings.NewReader(`{"version":"v0.4.0"}`))
	req.Header.Set("Content-Type", "application/json")
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	assertPluginStoreInstallResponseVersion(t, resp, "0.4.0")
	assertInstalledPluginStoreManifest(t, repo, "sample-provider", "0.4.0", "v0.4.0")
}

func TestInstallPluginFromStorePreservesGitHubReleaseErrorCodes(t *testing.T) {
	_, engine := setupPluginStoreInstallTest(t, fakePluginStoreHTTPClient{})

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install?version=0.6.0", nil)
	engine.ServeHTTP(resp, req)
	assertPluginStoreInstallError(t, resp, http.StatusBadGateway, "plugin_release_failed")

	_, invalidEngine := setupPluginStoreInstallTest(t, fakePluginStoreHTTPClient{
		"https://api.github.com/repos/author-name/sample-provider/releases/tags/v0.6.0": []byte(`{
			"tag_name": "not-a-version",
			"assets": []
		}`),
	})
	invalidResp := httptest.NewRecorder()
	invalidReq := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install?version=0.6.0", nil)
	invalidEngine.ServeHTTP(invalidResp, invalidReq)
	assertPluginStoreInstallError(t, invalidResp, http.StatusBadGateway, "plugin_release_invalid")
}

func TestInstallPluginFromStoreWritesDirectManifestConfig(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
			"dir":     t.TempDir(),
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	artifactURL := "https://downloads.example/sample-provider.zip"
	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(fakePluginStoreHTTPClient{
		pluginstore.DefaultRegistryURL: directRegistryJSON(artifactURL, "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"),
	})
	engine := gin.New()
	engine.POST("/plugin-store/:id/install", handler.InstallPluginFromStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	var body pluginInstallResponse
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if body.InstallType != pluginstore.InstallTypeDirect || body.Version != "0.4.0" {
		t.Fatalf("install response = %#v, want direct 0.4.0", body)
	}

	cfg, _, errConfig := repo.LoadConfigAsRuntimeConfig(context.Background())
	if errConfig != nil {
		t.Fatalf("LoadConfigAsRuntimeConfig() error = %v", errConfig)
	}
	item := cfg.Plugins.Configs["sample-provider"]
	storeNode := yamlMappingValue(&item.Raw, "store")
	if storeNode == nil {
		t.Fatal("plugin store manifest missing")
	}
	var manifest pluginstore.Manifest
	if errDecode := storeNode.Decode(&manifest); errDecode != nil {
		t.Fatalf("decode manifest: %v", errDecode)
	}
	if manifest.SchemaVersion != pluginstore.SchemaVersionV2 || manifest.InstallType() != pluginstore.InstallTypeDirect {
		t.Fatalf("manifest = %+v, want v2 direct", manifest)
	}
	if manifest.ReleaseTag != "" || manifest.Repository != "" {
		t.Fatalf("manifest release fields = %q/%q, want empty", manifest.ReleaseTag, manifest.Repository)
	}
	if manifest.SourceURL != pluginstore.DefaultRegistryURL {
		t.Fatalf("manifest source-url = %q, want default registry", manifest.SourceURL)
	}
	if len(manifest.Install.Artifacts) != 1 || manifest.Install.Artifacts[0].URL != "https://downloads.example/sample-provider.zip" {
		t.Fatalf("manifest artifacts = %+v, want fixed direct artifact", manifest.Install.Artifacts)
	}
}

func TestInstallPluginFromStoreWritesDirectManifestVersionFromVersions(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
			"dir":     t.TempDir(),
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(fakePluginStoreHTTPClient{
		pluginstore.DefaultRegistryURL: directRegistryJSONWithVersions(
			"https://downloads.example/sample-provider-0.4.0.zip",
			"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
			"https://downloads.example/sample-provider-0.3.0.zip",
			"abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
		),
	})
	engine := gin.New()
	engine.POST("/plugin-store/:id/install", handler.InstallPluginFromStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/install?version=0.3.0", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	var body pluginInstallResponse
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if body.InstallType != pluginstore.InstallTypeDirect || body.Version != "0.3.0" {
		t.Fatalf("install response = %#v, want direct 0.3.0", body)
	}

	cfg, _, errConfig := repo.LoadConfigAsRuntimeConfig(context.Background())
	if errConfig != nil {
		t.Fatalf("LoadConfigAsRuntimeConfig() error = %v", errConfig)
	}
	item := cfg.Plugins.Configs["sample-provider"]
	storeNode := yamlMappingValue(&item.Raw, "store")
	if storeNode == nil {
		t.Fatal("plugin store manifest missing")
	}
	var manifest pluginstore.Manifest
	if errDecode := storeNode.Decode(&manifest); errDecode != nil {
		t.Fatalf("decode manifest: %v", errDecode)
	}
	if manifest.Version != "0.3.0" || manifest.InstallType() != pluginstore.InstallTypeDirect {
		t.Fatalf("manifest = %+v, want direct 0.3.0", manifest)
	}
	if len(manifest.Install.Artifacts) != 1 || manifest.Install.Artifacts[0].URL != "https://downloads.example/sample-provider-0.3.0.zip" {
		t.Fatalf("manifest artifacts = %+v, want fixed version artifact", manifest.Install.Artifacts)
	}
}

type fakePluginStoreHTTPClient map[string][]byte

func (c fakePluginStoreHTTPClient) Do(req *http.Request) (*http.Response, error) {
	body, ok := c[req.URL.String()]
	if !ok {
		return &http.Response{
			StatusCode: http.StatusNotFound,
			Body:       io.NopCloser(strings.NewReader("not found")),
			Header:     make(http.Header),
			Request:    req,
		}, nil
	}
	return &http.Response{
		StatusCode: http.StatusOK,
		Body:       io.NopCloser(bytes.NewReader(body)),
		Header:     make(http.Header),
		Request:    req,
	}, nil
}

type authenticatedPluginStoreHTTPClient struct {
	responses     fakePluginStoreHTTPClient
	authorization map[string]string
}

func (c authenticatedPluginStoreHTTPClient) Do(req *http.Request) (*http.Response, error) {
	if want := c.authorization[req.URL.String()]; want != "" && req.Header.Get("Authorization") != want {
		return &http.Response{
			StatusCode: http.StatusUnauthorized,
			Body:       io.NopCloser(strings.NewReader("unauthorized")),
			Header:     make(http.Header),
			Request:    req,
		}, nil
	}
	return c.responses.Do(req)
}

func directRegistryJSON(artifactURL string, checksum string) []byte {
	return directRegistryJSONWithVersions(artifactURL, checksum, "", "")
}

func directRegistryJSONWithVersions(artifactURL string, checksum string, versionArtifactURL string, versionChecksum string) []byte {
	versionBlock := ""
	if versionArtifactURL != "" {
		versionBlock = `,
			"versions": [{
				"version": "0.3.0",
				"install": {
					"type": "direct",
					"artifacts": [{
						"goos": "linux",
						"goarch": "amd64",
						"url": "` + versionArtifactURL + `",
						"sha256": "` + versionChecksum + `"
					}]
				}
			}]`
	}
	return []byte(`{
		"schema_version": 2,
		"plugins": [{
			"id": "sample-provider",
			"name": "Sample Provider",
			"description": "Adds sample provider support.",
			"author": "author-name",
			"version": "0.4.0"` + versionBlock + `,
			"auth_required": true,
			"install": {
				"type": "direct",
				"artifacts": [{
					"goos": "linux",
					"goarch": "amd64",
					"url": "` + artifactURL + `",
					"sha256": "` + checksum + `"
				}]
			}
		}]
	}`)
}

func setupPluginStoreInstallTest(t *testing.T, httpClient fakePluginStoreHTTPClient) (*cluster.Repository, *gin.Engine) {
	t.Helper()

	db, cleanup := openManagementLogTestDB(t)
	t.Cleanup(cleanup)

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
			"dir":     t.TempDir(),
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	httpClient[pluginstore.DefaultRegistryURL] = []byte(`{
		"schema_version": 1,
		"plugins": [{
			"id": "sample-provider",
			"name": "Sample Provider",
			"description": "Adds sample provider support.",
			"author": "author-name",
			"repository": "https://github.com/author-name/sample-provider"
		}]
	}`)
	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(httpClient)
	engine := gin.New()
	engine.POST("/plugin-store/:id/install", handler.InstallPluginFromStore)
	return repo, engine
}

func assertPluginStoreInstallResponseVersion(t *testing.T, resp *httptest.ResponseRecorder, want string) {
	t.Helper()

	var body pluginInstallResponse
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if body.Version != want {
		t.Fatalf("response version = %q, want %q", body.Version, want)
	}
}

func assertPluginStoreInstallError(t *testing.T, resp *httptest.ResponseRecorder, wantStatus int, wantCode string) {
	t.Helper()

	if resp.Code != wantStatus {
		t.Fatalf("status = %d, body = %s, want %d", resp.Code, resp.Body.String(), wantStatus)
	}
	var body struct {
		Error string `json:"error"`
	}
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode error response: %v", errDecode)
	}
	if body.Error != wantCode {
		t.Fatalf("error = %q, want %q; body = %s", body.Error, wantCode, resp.Body.String())
	}
}

func assertInstalledPluginStoreManifest(t *testing.T, repo *cluster.Repository, id string, wantVersion string, wantReleaseTag string) {
	t.Helper()

	cfg, _, errConfig := repo.LoadConfigAsRuntimeConfig(context.Background())
	if errConfig != nil {
		t.Fatalf("LoadConfigAsRuntimeConfig() error = %v", errConfig)
	}
	item, okItem := cfg.Plugins.Configs[id]
	if !okItem {
		t.Fatalf("plugin config %q missing after install", id)
	}
	storeNode := yamlMappingValue(&item.Raw, "store")
	if storeNode == nil {
		t.Fatal("plugin store manifest missing")
	}
	var manifest pluginstore.Manifest
	if errDecode := storeNode.Decode(&manifest); errDecode != nil {
		t.Fatalf("decode manifest: %v", errDecode)
	}
	if manifest.Version != wantVersion || manifest.ReleaseTag != wantReleaseTag {
		t.Fatalf("manifest version fields = %q/%q, want %q/%q", manifest.Version, manifest.ReleaseTag, wantVersion, wantReleaseTag)
	}
}

func TestListPluginStoreReportsManifestStatus(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	customSourceURL := "https://plugins.example.test/registry.json?team=a&env=b"
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled":       true,
			"store-sources": []string{customSourceURL},
			"configs": map[string]any{
				"sample-provider": map[string]any{
					"enabled": true,
					"store": map[string]any{
						"id":          "sample-provider",
						"name":        "Sample Provider",
						"description": "Adds sample provider support.",
						"author":      "author-name",
						"version":     "0.2.0",
						"release-tag": "v0.2.0",
						"repository":  "https://github.com/author-name/sample-provider",
						"source-id":   pluginstore.DefaultSourceID,
						"source-name": pluginstore.DefaultSourceName,
						"source-url":  pluginstore.DefaultRegistryURL,
					},
				},
			},
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(fakePluginStoreHTTPClient{
		pluginstore.DefaultRegistryURL: []byte(`{
			"schema_version": 1,
			"plugins": [{
				"id": "sample-provider",
				"name": "Sample Provider",
				"description": "Adds sample provider support.",
				"author": "author-name",
				"version": "0.2.0",
				"repository": "https://github.com/author-name/sample-provider"
			}]
		}`),
		customSourceURL: []byte(`{
			"schema_version": 1,
			"plugins": []
		}`),
	})
	engine := gin.New()
	engine.GET("/plugin-store", handler.ListPluginStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/plugin-store", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	var body struct {
		Sources []struct {
			URL string `json:"url"`
		} `json:"sources"`
		Plugins []struct {
			ID               string `json:"id"`
			Installed        bool   `json:"installed"`
			InstalledVersion string `json:"installed_version"`
			Enabled          bool   `json:"enabled"`
			EffectiveEnabled bool   `json:"effective_enabled"`
		} `json:"plugins"`
	}
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if len(body.Plugins) != 1 {
		t.Fatalf("plugins len = %d, want 1", len(body.Plugins))
	}
	foundCustomSource := false
	for _, source := range body.Sources {
		if source.URL == customSourceURL {
			foundCustomSource = true
		}
		if strings.Contains(source.URL, "&amp;") {
			t.Fatalf("source URL was HTML-escaped: %q", source.URL)
		}
	}
	if !foundCustomSource {
		t.Fatalf("custom source URL missing from response: %+v", body.Sources)
	}
	entry := body.Plugins[0]
	if entry.ID != "sample-provider" || !entry.Installed || entry.InstalledVersion != "0.2.0" || !entry.Enabled || !entry.EffectiveEnabled {
		t.Fatalf("plugin entry = %+v, want manifest installed status", entry)
	}
}

func TestListPluginStoreReportsDirectMetadata(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(fakePluginStoreHTTPClient{
		pluginstore.DefaultRegistryURL: directRegistryJSON("https://downloads.example/sample-provider.zip", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"),
	})
	engine := gin.New()
	engine.GET("/plugin-store", handler.ListPluginStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/plugin-store", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	var body pluginStoreListResponse
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if strings.Contains(resp.Body.String(), "auth_configured") {
		t.Fatalf("response retained removed auth_configured field: %s", resp.Body.String())
	}
	if len(body.Plugins) != 1 {
		t.Fatalf("plugins len = %d, want 1", len(body.Plugins))
	}
	entry := body.Plugins[0]
	if entry.InstallType != pluginstore.InstallTypeDirect || !entry.AuthRequired {
		t.Fatalf("plugin entry = %+v, want direct metadata", entry)
	}
	if len(entry.Platforms) != 1 || entry.Platforms[0].GOOS != "linux" || entry.Platforms[0].GOARCH != "amd64" {
		t.Fatalf("platforms = %+v, want linux/amd64", entry.Platforms)
	}
}

func TestListPluginStoreReportsGitHubReleaseMetadata(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{"enabled": true},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(fakePluginStoreHTTPClient{
		pluginstore.DefaultRegistryURL: []byte(`{
			"schema_version": 1,
			"plugins": [{
				"id": "sample-provider",
				"name": "Sample Provider",
				"description": "Adds sample provider support.",
				"author": "author-name",
				"repository": "https://github.com/author-name/sample-provider",
				"auth_required": true
			}]
		}`),
	})
	engine := gin.New()
	engine.GET("/plugin-store", handler.ListPluginStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/plugin-store", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	var body pluginStoreListResponse
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if len(body.Plugins) != 1 {
		t.Fatalf("plugins len = %d, want 1", len(body.Plugins))
	}
	entry := body.Plugins[0]
	if entry.InstallType != pluginstore.InstallTypeGitHubRelease || !entry.AuthRequired {
		t.Fatalf("plugin entry = %+v, want github-release metadata", entry)
	}
}

func TestListPluginStoreUsesDatabaseAuthForPrivateRegistry(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	privateRegistryURL := "https://plugins.example/private/registry.json"
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled":       true,
			"store-sources": []string{privateRegistryURL},
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}
	if _, errCreate := pluginauth.NewService(repo).Create(context.Background(), pluginauth.CreateInput{
		Name:     "private registry",
		Match:    "https://plugins.example/private/",
		ApplyTo:  []string{pluginstore.RequestKindRegistry},
		AuthType: pluginstore.AuthTypeBearer,
		Token:    pluginstore.Secret("registry-token"),
	}); errCreate != nil {
		t.Fatalf("Create() error = %v", errCreate)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	handler.SetPluginStoreHTTPClient(authenticatedPluginStoreHTTPClient{
		responses: fakePluginStoreHTTPClient{
			pluginstore.DefaultRegistryURL: []byte(`{"schema_version":1,"plugins":[]}`),
			privateRegistryURL: []byte(`{
				"schema_version": 1,
				"plugins": [{
					"id": "private-provider",
					"name": "Private Provider",
					"description": "Private plugin.",
					"author": "owner",
					"repository": "https://github.com/owner/private-provider"
				}]
			}`),
		},
		authorization: map[string]string{privateRegistryURL: "Bearer registry-token"},
	})
	engine := gin.New()
	engine.GET("/plugin-store", handler.ListPluginStore)

	resp := httptest.NewRecorder()
	engine.ServeHTTP(resp, httptest.NewRequest(http.MethodGet, "/plugin-store", nil))
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}
	var body pluginStoreListResponse
	if errDecode := json.Unmarshal(resp.Body.Bytes(), &body); errDecode != nil {
		t.Fatalf("decode response: %v", errDecode)
	}
	if len(body.Plugins) != 1 || body.Plugins[0].ID != "private-provider" {
		t.Fatalf("plugins = %+v, want private-provider", body.Plugins)
	}
}

func TestUninstallPluginFromStoreRemovesConfigAndCreatesTask(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
			"configs": map[string]any{
				"sample-provider": map[string]any{
					"enabled": true,
					"store": map[string]any{
						"id":          "sample-provider",
						"name":        "Sample Provider",
						"description": "Adds sample provider support.",
						"author":      "author-name",
						"version":     "0.2.0",
						"release-tag": "v0.2.0",
						"repository":  "https://github.com/author-name/sample-provider",
					},
				},
			},
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	engine := gin.New()
	engine.POST("/plugin-store/:id/uninstall", handler.UninstallPluginFromStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/uninstall", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}

	cfg, _, errConfig := repo.LoadConfigAsRuntimeConfig(context.Background())
	if errConfig != nil {
		t.Fatalf("LoadConfigAsRuntimeConfig() error = %v", errConfig)
	}
	if _, ok := cfg.Plugins.Configs["sample-provider"]; ok {
		t.Fatal("plugin config still exists after delete")
	}
	tasks, errTasks := repo.ListPendingPluginTasks(context.Background(), node.PluginStatusNodeTypeCPA, "node-1")
	if errTasks != nil {
		t.Fatalf("ListPendingPluginTasks() error = %v", errTasks)
	}
	if len(tasks) != 1 || tasks[0].Operation != node.PluginTaskOperationDelete || tasks[0].PluginID != "sample-provider" || tasks[0].TargetNodeType != node.PluginTaskTargetAll {
		t.Fatalf("tasks = %+v, want one global delete task", tasks)
	}
}

func TestUninstallPluginFromStoreIgnoresTargetQueryAndCreatesGlobalTask(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
			"configs": map[string]any{
				"sample-provider": map[string]any{
					"enabled": true,
					"store": map[string]any{
						"id":          "sample-provider",
						"name":        "Sample Provider",
						"description": "Adds sample provider support.",
						"author":      "author-name",
						"version":     "0.2.0",
						"release-tag": "v0.2.0",
						"repository":  "https://github.com/author-name/sample-provider",
					},
				},
			},
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	engine := gin.New()
	engine.POST("/plugin-store/:id/uninstall", handler.UninstallPluginFromStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/uninstall?node_id=node-1&remove_config=false", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}

	cfg, _, errConfig := repo.LoadConfigAsRuntimeConfig(context.Background())
	if errConfig != nil {
		t.Fatalf("LoadConfigAsRuntimeConfig() error = %v", errConfig)
	}
	if _, ok := cfg.Plugins.Configs["sample-provider"]; ok {
		t.Fatal("plugin config still exists after delete")
	}

	for _, nodeID := range []string{"node-1", "node-2"} {
		tasks, errTasks := repo.ListPendingPluginTasks(context.Background(), node.PluginStatusNodeTypeCPA, nodeID)
		if errTasks != nil {
			t.Fatalf("ListPendingPluginTasks(%s) error = %v", nodeID, errTasks)
		}
		if len(tasks) != 1 || tasks[0].Operation != node.PluginTaskOperationDelete || tasks[0].PluginID != "sample-provider" || tasks[0].TargetNodeType != node.PluginTaskTargetAll || tasks[0].TargetNodeID != "" {
			t.Fatalf("%s tasks = %+v, want one global delete task", nodeID, tasks)
		}
	}
}

func TestUninstallPluginFromStoreIgnoresInvalidTargetQuery(t *testing.T) {
	db, cleanup := openManagementLogTestDB(t)
	defer cleanup()

	repo := cluster.NewRepository(db)
	if errReplace := repo.ReplaceConfigSnapshot(context.Background(), map[string]any{
		"plugins": map[string]any{
			"enabled": true,
			"configs": map[string]any{
				"sample-provider": map[string]any{
					"enabled": true,
					"store": map[string]any{
						"id":          "sample-provider",
						"name":        "Sample Provider",
						"description": "Adds sample provider support.",
						"author":      "author-name",
						"version":     "0.2.0",
						"release-tag": "v0.2.0",
						"repository":  "https://github.com/author-name/sample-provider",
					},
				},
			},
		},
	}); errReplace != nil {
		t.Fatalf("ReplaceConfigSnapshot() error = %v", errReplace)
	}

	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	engine := gin.New()
	engine.POST("/plugin-store/:id/uninstall", handler.UninstallPluginFromStore)

	resp := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/plugin-store/sample-provider/uninstall?node_id=node-1&node_type=bad", nil)
	engine.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", resp.Code, resp.Body.String())
	}

	cfg, _, errConfig := repo.LoadConfigAsRuntimeConfig(context.Background())
	if errConfig != nil {
		t.Fatalf("LoadConfigAsRuntimeConfig() error = %v", errConfig)
	}
	if _, ok := cfg.Plugins.Configs["sample-provider"]; ok {
		t.Fatal("plugin config still exists after delete")
	}
	tasks, errTasks := repo.ListPendingPluginTasks(context.Background(), node.PluginStatusNodeTypeCPA, "node-1")
	if errTasks != nil {
		t.Fatalf("ListPendingPluginTasks() error = %v", errTasks)
	}
	if len(tasks) != 1 || tasks[0].Operation != node.PluginTaskOperationDelete || tasks[0].PluginID != "sample-provider" || tasks[0].TargetNodeType != node.PluginTaskTargetAll || tasks[0].TargetNodeID != "" {
		t.Fatalf("tasks = %+v, want one global delete task", tasks)
	}
}
