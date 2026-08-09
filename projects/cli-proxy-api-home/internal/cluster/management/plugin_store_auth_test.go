package management

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"github.com/router-for-me/CLIProxyAPIHome/internal/pluginauth"
	"gorm.io/gorm"
)

func TestPluginStoreAuthCRUDKeepsSecretsWriteOnly(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db, errOpen := cluster.OpenSQLite(context.Background(), filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpen)
	}
	sqlDB, _ := db.DB()
	t.Cleanup(func() { _ = sqlDB.Close() })
	if errMigrate := cluster.AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	repo := cluster.NewRepository(db)
	handler := NewHandler(repo, nil, "127.0.0.1", 0)
	engine := gin.New()
	engine.GET("/plugin-store-auth", handler.ListPluginStoreAuth)
	engine.POST("/plugin-store-auth", handler.CreatePluginStoreAuth)
	engine.GET("/plugin-store-auth/:id", handler.GetPluginStoreAuth)
	engine.PATCH("/plugin-store-auth/:id", handler.UpdatePluginStoreAuth)
	engine.DELETE("/plugin-store-auth/:id", handler.DeletePluginStoreAuth)

	create := httptest.NewRecorder()
	engine.ServeHTTP(create, httptest.NewRequest(http.MethodPost, "/plugin-store-auth", strings.NewReader(`{
		"name":"private","match":"https://downloads.example/private/","apply_to":["artifact"],
		"auth_type":"bearer","token":"top-secret-token","enabled":false
	}`)))
	if create.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body=%s", create.Code, create.Body.String())
	}
	assertNoPluginStoreSecret(t, create.Body.String())
	var created pluginauth.Entry
	if errDecode := json.Unmarshal(create.Body.Bytes(), &created); errDecode != nil {
		t.Fatalf("decode create response: %v", errDecode)
	}
	if created.ID == 0 || created.Enabled || !created.CredentialsConfigured {
		t.Fatalf("created entry = %#v", created)
	}
	path := "/plugin-store-auth/" + strconv.FormatUint(uint64(created.ID), 10)
	get := httptest.NewRecorder()
	engine.ServeHTTP(get, httptest.NewRequest(http.MethodGet, path, nil))
	if get.Code != http.StatusOK {
		t.Fatalf("get status = %d, body=%s", get.Code, get.Body.String())
	}
	var fetched pluginauth.Entry
	if errDecode := json.Unmarshal(get.Body.Bytes(), &fetched); errDecode != nil {
		t.Fatalf("decode get response: %v", errDecode)
	}
	if fetched.Enabled {
		t.Fatalf("fetched entry enabled = true, want false")
	}

	patch := httptest.NewRecorder()
	engine.ServeHTTP(patch, httptest.NewRequest(http.MethodPatch, path, strings.NewReader(`{"name":"renamed","enabled":true}`)))
	if patch.Code != http.StatusOK {
		t.Fatalf("patch status = %d, body=%s", patch.Code, patch.Body.String())
	}
	assertNoPluginStoreSecret(t, patch.Body.String())
	rules, errResolved := pluginauth.NewService(repo).Resolved(context.Background())
	if errResolved != nil {
		t.Fatalf("Resolved() error = %v", errResolved)
	}
	defer func() {
		for index := range rules {
			rules[index].Clear()
		}
	}()
	if len(rules) != 1 || string(rules[0].Token) != "top-secret-token" {
		t.Fatalf("resolved rules = %#v, want preserved token", rules)
	}

	list := httptest.NewRecorder()
	engine.ServeHTTP(list, httptest.NewRequest(http.MethodGet, "/plugin-store-auth", nil))
	if list.Code != http.StatusOK {
		t.Fatalf("list status = %d, body=%s", list.Code, list.Body.String())
	}
	assertNoPluginStoreSecret(t, list.Body.String())

	deleteResponse := httptest.NewRecorder()
	engine.ServeHTTP(deleteResponse, httptest.NewRequest(http.MethodDelete, path, nil))
	if deleteResponse.Code != http.StatusOK {
		t.Fatalf("delete status = %d, body=%s", deleteResponse.Code, deleteResponse.Body.String())
	}
}

func assertNoPluginStoreSecret(t *testing.T, body string) {
	t.Helper()
	for _, forbidden := range []string{"top-secret-token", "encrypted_credentials", "ciphertext", `"token"`} {
		if strings.Contains(body, forbidden) {
			t.Fatalf("response leaked secret field %q: %s", forbidden, body)
		}
	}
}

func TestRespondPluginStoreAuthErrorClassifiesErrors(t *testing.T) {
	gin.SetMode(gin.TestMode)
	tests := []struct {
		name       string
		err        error
		wantStatus int
		wantCode   string
	}{
		{name: "validation", err: pluginauth.ErrInvalidInput, wantStatus: http.StatusUnprocessableEntity, wantCode: "plugin_store_auth_invalid"},
		{name: "not found", err: gorm.ErrRecordNotFound, wantStatus: http.StatusNotFound, wantCode: "plugin_store_auth_failed"},
		{name: "conflict", err: cluster.ErrPluginStoreAuthConflict, wantStatus: http.StatusConflict, wantCode: "plugin_store_auth_failed"},
		{name: "system", err: errors.New("database unavailable"), wantStatus: http.StatusInternalServerError, wantCode: "plugin_store_auth_failed"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			recorder := httptest.NewRecorder()
			ctx, _ := gin.CreateTestContext(recorder)
			respondPluginStoreAuthError(ctx, "plugin_store_auth_failed", test.err)
			if recorder.Code != test.wantStatus {
				t.Fatalf("status = %d, want %d", recorder.Code, test.wantStatus)
			}
			var response struct {
				Error string `json:"error"`
			}
			if errDecode := json.Unmarshal(recorder.Body.Bytes(), &response); errDecode != nil {
				t.Fatalf("decode response: %v", errDecode)
			}
			if response.Error != test.wantCode {
				t.Fatalf("error code = %q, want %q", response.Error, test.wantCode)
			}
		})
	}
}

func TestDecodePluginStoreAuthJSONClearsRawAndDecodedSecrets(t *testing.T) {
	tests := []struct {
		name    string
		body    string
		wantErr bool
	}{
		{
			name: "success",
			body: `{"token":"token-secret","username":"user-secret","password":"password-secret","header_value":"header-secret"}`,
		},
		{
			name:    "partial decode failure",
			body:    `{"token":"partial-secret","enabled":"not-a-boolean"}`,
			wantErr: true,
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			raw := []byte(test.body)
			rawBacking := raw
			var secretBackings [][]byte
			var errDecode error
			func() {
				var request createPluginStoreAuthRequest
				defer request.Clear()
				errDecode = decodePluginStoreAuthJSON(raw, &request)
				secretBackings = [][]byte{
					request.Token.Value(),
					request.Username.Value(),
					request.Password.Value(),
					request.HeaderValue.Value(),
				}
			}()
			if (errDecode != nil) != test.wantErr {
				t.Fatalf("decode error = %v, wantErr %v", errDecode, test.wantErr)
			}
			if errDecode != nil && strings.Contains(errDecode.Error(), "partial-secret") {
				t.Fatalf("decode error leaked secret: %v", errDecode)
			}
			if len(secretBackings[0]) == 0 {
				t.Fatal("token secret was not decoded before cleanup")
			}
			assertClearedPluginStoreAuthBytes(t, "raw request", rawBacking)
			for index, backing := range secretBackings {
				assertClearedPluginStoreAuthBytes(t, "decoded secret "+strconv.Itoa(index), backing)
			}
		})
	}
}

func TestDecodePluginStoreAuthJSONRejectsUnknownAndTrailingData(t *testing.T) {
	for _, body := range []string{
		`{"name":"test","unknown":"value"}`,
		`{"name":"test"} {"name":"second"}`,
		`null`,
		`[]`,
	} {
		raw := []byte(body)
		rawBacking := raw
		var request createPluginStoreAuthRequest
		if errDecode := decodePluginStoreAuthJSON(raw, &request); errDecode == nil {
			t.Fatalf("decodePluginStoreAuthJSON(%q) error = nil", body)
		}
		request.Clear()
		assertClearedPluginStoreAuthBytes(t, "invalid request", rawBacking)
	}
}

func TestDecodePluginStoreAuthRequestRejectsOversizedBody(t *testing.T) {
	recorder := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(recorder)
	ctx.Request = httptest.NewRequest(http.MethodPost, "/plugin-store-auth", strings.NewReader(strings.Repeat(" ", int(pluginStoreAuthMaxRequestBodySize)+1)))
	var request createPluginStoreAuthRequest
	errDecode := decodePluginStoreAuthRequest(ctx, &request)
	if errDecode == nil {
		t.Fatal("decodePluginStoreAuthRequest() error = nil")
	}
	var maxBytesError *http.MaxBytesError
	if !errors.As(errDecode, &maxBytesError) {
		t.Fatalf("decodePluginStoreAuthRequest() error = %v, want MaxBytesError", errDecode)
	}
	respondPluginStoreAuthRequestError(ctx, errDecode)
	if recorder.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusRequestEntityTooLarge)
	}
}

func TestPluginStoreAuthIDRejectsOverflow(t *testing.T) {
	recorder := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(recorder)
	ctx.Params = gin.Params{{Key: "id", Value: "18446744073709551615"}}
	if _, okID := pluginStoreAuthID(ctx); okID {
		t.Fatal("pluginStoreAuthID() ok = true for overflow")
	}
	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusBadRequest)
	}
}

func TestDecodePluginStoreAuthRequestClearsPartialBodyOnReadError(t *testing.T) {
	reader := &pluginStoreAuthReadErrorReader{payload: []byte(`{"token":"partial-secret"}`)}
	recorder := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(recorder)
	ctx.Request = httptest.NewRequest(http.MethodPost, "/plugin-store-auth", nil)
	ctx.Request.Body = io.NopCloser(reader)

	var request createPluginStoreAuthRequest
	defer request.Clear()
	if errDecode := decodePluginStoreAuthRequest(ctx, &request); errDecode == nil {
		t.Fatal("decode error = nil, want read failure")
	}
	assertClearedPluginStoreAuthBytes(t, "partial request body", reader.destination)
}

func TestUpdatePluginStoreAuthRequestPreservesSecretPresence(t *testing.T) {
	tests := []struct {
		name        string
		body        string
		wantPresent bool
		wantValue   string
	}{
		{name: "omitted", body: `{}`},
		{name: "null", body: `{"token":null}`},
		{name: "empty", body: `{"token":""}`, wantPresent: true},
		{name: "value", body: `{"token":"replacement"}`, wantPresent: true, wantValue: "replacement"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var request updatePluginStoreAuthRequest
			defer request.Clear()
			raw := []byte(test.body)
			if errDecode := decodePluginStoreAuthJSON(raw, &request); errDecode != nil {
				t.Fatalf("decode error = %v", errDecode)
			}
			if (request.Token.Pointer() != nil) != test.wantPresent {
				t.Fatalf("token present = %v, want %v", request.Token.Pointer() != nil, test.wantPresent)
			}
			if request.Token.Pointer() != nil && string(request.Token.Value()) != test.wantValue {
				t.Fatalf("token value = %q, want %q", string(request.Token.Value()), test.wantValue)
			}
		})
	}
}

func TestUpdatePluginStoreAuthRequestClearsSecretOverwrittenByNull(t *testing.T) {
	raw := []byte(`{"token":"discarded-secret","token":null}`)
	var request struct {
		Token recordingOptionalPluginStoreAuthRequestSecret `json:"token"`
	}
	if errDecode := decodePluginStoreAuthJSON(raw, &request); errDecode != nil {
		t.Fatalf("decode error = %v", errDecode)
	}
	if request.Token.Pointer() != nil {
		t.Fatal("token present = true, want false after duplicate null")
	}
	if len(request.Token.overwrittenBackings) != 1 {
		t.Fatalf("overwritten secret backings = %d, want 1", len(request.Token.overwrittenBackings))
	}
	assertClearedPluginStoreAuthBytes(t, "overwritten secret", request.Token.overwrittenBackings[0])
}

type recordingOptionalPluginStoreAuthRequestSecret struct {
	optionalPluginStoreAuthRequestSecret
	overwrittenBackings [][]byte
}

type pluginStoreAuthReadErrorReader struct {
	payload     []byte
	destination []byte
}

func (r *pluginStoreAuthReadErrorReader) Read(destination []byte) (int, error) {
	if len(r.payload) == 0 {
		return 0, errors.New("request read failed")
	}
	n := copy(destination, r.payload)
	r.destination = destination[:n]
	r.payload = nil
	return n, errors.New("request read failed")
}

func (s *recordingOptionalPluginStoreAuthRequestSecret) UnmarshalJSON(raw []byte) error {
	if value := s.Value(); value != nil {
		s.overwrittenBackings = append(s.overwrittenBackings, value)
	}
	return s.optionalPluginStoreAuthRequestSecret.UnmarshalJSON(raw)
}

func assertClearedPluginStoreAuthBytes(t *testing.T, name string, value []byte) {
	t.Helper()
	for index, item := range value {
		if item != 0 {
			t.Fatalf("%s byte %d = %d, want zero", name, index, item)
		}
	}
}
