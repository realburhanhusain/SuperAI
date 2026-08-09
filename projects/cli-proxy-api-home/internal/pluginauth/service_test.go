package pluginauth

import (
	"bytes"
	"context"
	"errors"
	"path/filepath"
	"testing"

	"github.com/router-for-me/CLIProxyAPI/v7/sdk/pluginstore"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"gorm.io/gorm"
)

func TestServiceEncryptsCredentialsWithAADAndPreservesOmittedSecret(t *testing.T) {
	service, db := newTestService(t)
	created, errCreate := service.Create(context.Background(), CreateInput{
		Name: "private artifacts", Match: "https://downloads.example/private/",
		ApplyTo: []string{pluginstore.RequestKindArtifact}, AuthType: pluginstore.AuthTypeBearer,
		Token: pluginstore.Secret("first-token"),
	})
	if errCreate != nil {
		t.Fatalf("Create() error = %v", errCreate)
	}
	if !created.CredentialsConfigured {
		t.Fatalf("created entry = %#v, want credentials configured", created)
	}
	var record cluster.PluginStoreAuthRecord
	if errFirst := db.First(&record, created.ID).Error; errFirst != nil {
		t.Fatalf("First() error = %v", errFirst)
	}
	if bytes.Contains(record.EncryptedCredentials, []byte("first-token")) {
		t.Fatal("encrypted credentials contain plaintext token")
	}
	name := "renamed"
	if _, errUpdate := service.Update(context.Background(), created.ID, UpdateInput{Name: &name}); errUpdate != nil {
		t.Fatalf("Update() error = %v", errUpdate)
	}
	rules, errResolved := service.Resolved(context.Background())
	if errResolved != nil {
		t.Fatalf("Resolved() error = %v", errResolved)
	}
	defer pluginstore.ClearResolvedAuthConfigs(rules)
	if len(rules) != 1 || string(rules[0].Token) != "first-token" {
		t.Fatalf("resolved rules = %#v, want preserved token", rules)
	}
	if errTamper := db.Model(&cluster.PluginStoreAuthRecord{}).Where("id = ?", created.ID).Update("auth_type", pluginstore.AuthTypeBasic).Error; errTamper != nil {
		t.Fatalf("tamper auth type: %v", errTamper)
	}
	if _, errTampered := service.Resolved(context.Background()); errTampered == nil {
		t.Fatal("Resolved() error = nil after AAD auth type tamper")
	}
}

func TestServiceSwitchToNoneRemovesCiphertextAndTypeChangeRequiresCredentials(t *testing.T) {
	service, db := newTestService(t)
	created, errCreate := service.Create(context.Background(), CreateInput{
		Name: "private", Match: "https://downloads.example/", AuthType: pluginstore.AuthTypeBearer, Token: pluginstore.Secret("token"),
	})
	if errCreate != nil {
		t.Fatalf("Create() error = %v", errCreate)
	}
	basic := pluginstore.AuthTypeBasic
	if _, errUpdate := service.Update(context.Background(), created.ID, UpdateInput{AuthType: &basic}); !errors.Is(errUpdate, ErrInvalidInput) {
		t.Fatalf("Update(type only) error = %v, want ErrInvalidInput", errUpdate)
	}
	none := pluginstore.AuthTypeNone
	updated, errNone := service.Update(context.Background(), created.ID, UpdateInput{AuthType: &none})
	if errNone != nil {
		t.Fatalf("Update(none) error = %v", errNone)
	}
	if updated.CredentialsConfigured {
		t.Fatalf("updated entry = %#v, want no configured credentials", updated)
	}
	var record cluster.PluginStoreAuthRecord
	if errFirst := db.First(&record, created.ID).Error; errFirst != nil {
		t.Fatalf("First() error = %v", errFirst)
	}
	if len(record.EncryptedCredentials) != 0 {
		t.Fatalf("none ciphertext length = %d, want zero", len(record.EncryptedCredentials))
	}
}

func TestServiceSharesEncryptedAuthAcrossHomeConnections(t *testing.T) {
	path := filepath.Join(t.TempDir(), "home.db")
	dbA, errOpenA := cluster.OpenSQLite(context.Background(), path)
	if errOpenA != nil {
		t.Fatalf("OpenSQLite(A) error = %v", errOpenA)
	}
	dbB, errOpenB := cluster.OpenSQLite(context.Background(), path)
	if errOpenB != nil {
		t.Fatalf("OpenSQLite(B) error = %v", errOpenB)
	}
	for _, db := range []*gorm.DB{dbA, dbB} {
		sqlDB, _ := db.DB()
		t.Cleanup(func() { _ = sqlDB.Close() })
	}
	if errMigrate := cluster.AutoMigrate(dbA); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	serviceA := NewService(cluster.NewRepository(dbA))
	serviceB := NewService(cluster.NewRepository(dbB))
	if _, errCreate := serviceA.Create(context.Background(), CreateInput{
		Name: "shared", Match: "https://downloads.example/", AuthType: pluginstore.AuthTypeHeader,
		HeaderName: "X-Plugin-Token", HeaderValue: pluginstore.Secret("shared-secret"),
	}); errCreate != nil {
		t.Fatalf("Create() error = %v", errCreate)
	}
	rules, errResolved := serviceB.Resolved(context.Background())
	if errResolved != nil {
		t.Fatalf("Resolved(B) error = %v", errResolved)
	}
	defer pluginstore.ClearResolvedAuthConfigs(rules)
	if len(rules) != 1 || string(rules[0].HeaderValue) != "shared-secret" {
		t.Fatalf("resolved rules = %#v, want shared secret", rules)
	}
}

func TestServiceRejectsInsecureMatch(t *testing.T) {
	service, _ := newTestService(t)
	if _, errCreate := service.Create(context.Background(), CreateInput{
		Name: "insecure", Match: "http://downloads.example/", AuthType: pluginstore.AuthTypeBearer, Token: pluginstore.Secret("token"),
	}); !errors.Is(errCreate, ErrInvalidInput) {
		t.Fatalf("Create() error = %v, want ErrInvalidInput", errCreate)
	}
}

func TestServiceRejectsInvalidHTTPHeaderCredentials(t *testing.T) {
	service, _ := newTestService(t)
	if _, errCreate := service.Create(context.Background(), CreateInput{
		Name: "invalid header", Match: "https://downloads.example/", AuthType: pluginstore.AuthTypeHeader,
		HeaderName: "Bad Header", HeaderValue: pluginstore.Secret("value"),
	}); !errors.Is(errCreate, ErrInvalidInput) {
		t.Fatalf("Create(invalid header name) error = %v, want ErrInvalidInput", errCreate)
	}
	if _, errCreate := service.Create(context.Background(), CreateInput{
		Name: "invalid bearer", Match: "https://downloads.example/", AuthType: pluginstore.AuthTypeBearer,
		Token: pluginstore.Secret{'t', 'o', 'k', 'e', 'n', 0},
	}); !errors.Is(errCreate, ErrInvalidInput) {
		t.Fatalf("Create(invalid bearer token) error = %v, want ErrInvalidInput", errCreate)
	}
}

func TestServiceResolvedRejectsInvalidStoredHeaderName(t *testing.T) {
	service, db := newTestService(t)
	created, errCreate := service.Create(context.Background(), CreateInput{
		Name: "stored header", Match: "https://downloads.example/", AuthType: pluginstore.AuthTypeHeader,
		HeaderName: "X-Plugin-Token", HeaderValue: pluginstore.Secret("value"),
	})
	if errCreate != nil {
		t.Fatalf("Create() error = %v", errCreate)
	}
	if errUpdate := db.Model(&cluster.PluginStoreAuthRecord{}).Where("id = ?", created.ID).Update("header_name", "Bad Header").Error; errUpdate != nil {
		t.Fatalf("tamper header name: %v", errUpdate)
	}
	if _, errResolved := service.Resolved(context.Background()); errResolved == nil {
		t.Fatal("Resolved() error = nil for invalid stored header name")
	}
}

func TestServiceConsumesInputSecretBackings(t *testing.T) {
	service, _ := newTestService(t)
	createToken := pluginstore.Secret("create-secret")
	createBacking := createToken
	created, errCreate := service.Create(context.Background(), CreateInput{
		Name: "private", Match: "https://downloads.example/", AuthType: pluginstore.AuthTypeBearer, Token: createToken,
	})
	if errCreate != nil {
		t.Fatalf("Create() error = %v", errCreate)
	}
	assertClearedSecret(t, "create token", createBacking)

	replacement := pluginstore.Secret("replacement-secret")
	replacementBacking := replacement
	if _, errUpdate := service.Update(context.Background(), created.ID, UpdateInput{Token: &replacement}); errUpdate != nil {
		t.Fatalf("Update() error = %v", errUpdate)
	}
	assertClearedSecret(t, "update token", replacementBacking)

	invalidToken := pluginstore.Secret("invalid-secret")
	invalidBacking := invalidToken
	if _, errInvalid := service.Create(context.Background(), CreateInput{
		Name: "invalid", Match: "http://downloads.example/", AuthType: pluginstore.AuthTypeBearer, Token: invalidToken,
	}); !errors.Is(errInvalid, ErrInvalidInput) {
		t.Fatalf("Create(invalid) error = %v, want ErrInvalidInput", errInvalid)
	}
	assertClearedSecret(t, "invalid token", invalidBacking)
}

func TestCredentialPlaintextEncodingRoundTrip(t *testing.T) {
	want := credentials{
		Token:       pluginstore.Secret("token-secret"),
		Username:    pluginstore.Secret("username-secret"),
		Password:    pluginstore.Secret("password-secret"),
		HeaderValue: pluginstore.Secret("header-secret"),
	}
	defer want.Clear()
	raw, errEncode := encodeCredentialPlaintext(want)
	if errEncode != nil {
		t.Fatalf("encodeCredentialPlaintext() error = %v", errEncode)
	}
	defer clearBytes(raw)
	got, errDecode := decodeCredentialPlaintext(raw)
	if errDecode != nil {
		t.Fatalf("decodeCredentialPlaintext() error = %v", errDecode)
	}
	defer got.Clear()
	if !bytes.Equal(got.Token, want.Token) || !bytes.Equal(got.Username, want.Username) ||
		!bytes.Equal(got.Password, want.Password) || !bytes.Equal(got.HeaderValue, want.HeaderValue) {
		t.Fatalf("decoded credentials = %#v, want round trip", got)
	}
}

func assertClearedSecret(t *testing.T, name string, value pluginstore.Secret) {
	t.Helper()
	for index, item := range value {
		if item != 0 {
			t.Fatalf("%s byte %d = %d, want zero", name, index, item)
		}
	}
}

func newTestService(t *testing.T) (*Service, *gorm.DB) {
	t.Helper()
	db, errOpen := cluster.OpenSQLite(context.Background(), filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpen)
	}
	sqlDB, _ := db.DB()
	t.Cleanup(func() { _ = sqlDB.Close() })
	if errMigrate := cluster.AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	return NewService(cluster.NewRepository(db)), db
}
