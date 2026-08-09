package cluster

import (
	"bytes"
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"

	"gorm.io/gorm"
)

func TestPluginStoreAuthKeySharedAcrossIndependentSQLiteConnections(t *testing.T) {
	path := filepath.Join(t.TempDir(), "home.db")
	dbA, errOpenA := OpenSQLite(context.Background(), path)
	if errOpenA != nil {
		t.Fatalf("OpenSQLite(A) error = %v", errOpenA)
	}
	dbB, errOpenB := OpenSQLite(context.Background(), path)
	if errOpenB != nil {
		t.Fatalf("OpenSQLite(B) error = %v", errOpenB)
	}
	for _, db := range []*gorm.DB{dbA, dbB} {
		sqlDB, _ := db.DB()
		t.Cleanup(func() { _ = sqlDB.Close() })
	}
	if errMigrate := AutoMigrate(dbA); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	repoA := NewRepository(dbA)
	repoB := NewRepository(dbB)
	var keyA, keyB []byte
	var versionA, versionB int
	var errA, errB error
	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		keyA, versionA, errA = repoA.EnsurePluginStoreAuthKey(context.Background())
	}()
	go func() {
		defer wg.Done()
		keyB, versionB, errB = repoB.EnsurePluginStoreAuthKey(context.Background())
	}()
	wg.Wait()
	defer clearBytes(keyA)
	defer clearBytes(keyB)
	if errA != nil || errB != nil {
		t.Fatalf("EnsurePluginStoreAuthKey() errors = %v / %v", errA, errB)
	}
	if versionA != pluginStoreAuthKeyVersion || versionB != pluginStoreAuthKeyVersion || !bytes.Equal(keyA, keyB) {
		t.Fatalf("keys differ across connections: version=%d/%d equal=%v", versionA, versionB, bytes.Equal(keyA, keyB))
	}
}

func TestAutoMigrateCreatesPluginStoreAuthRevisionIndex(t *testing.T) {
	db, errOpen := OpenSQLite(context.Background(), filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpen)
	}
	sqlDB, _ := db.DB()
	t.Cleanup(func() { _ = sqlDB.Close() })
	if errMigrate := AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	if !db.Migrator().HasIndex(&ClusterEventRecord{}, "idx_cluster_events_scope_id") {
		t.Fatal("AutoMigrate() did not create idx_cluster_events_scope_id")
	}
	var columns []struct {
		Sequence int    `gorm:"column:seqno"`
		Name     string `gorm:"column:name"`
	}
	if errColumns := db.Raw("PRAGMA index_info('idx_cluster_events_scope_id')").Scan(&columns).Error; errColumns != nil {
		t.Fatalf("read idx_cluster_events_scope_id columns: %v", errColumns)
	}
	if len(columns) != 2 || columns[0].Sequence != 0 || columns[0].Name != "scope" || columns[1].Sequence != 1 || columns[1].Name != "id" {
		t.Fatalf("idx_cluster_events_scope_id columns = %#v, want scope,id", columns)
	}
}

func TestListPluginStoreAuthUsesDatabaseIDOrder(t *testing.T) {
	repo, _ := newPluginStoreAuthTestRepository(t)
	first := &PluginStoreAuthRecord{Name: "first", Match: "https://first.example/", AuthType: "none", Enabled: true}
	second := &PluginStoreAuthRecord{Name: "second", Match: "https://second.example/", AuthType: "none", Enabled: true}
	seal := func(uint) ([]byte, int, error) { return nil, pluginStoreAuthKeyVersion, nil }
	if errCreate := repo.CreatePluginStoreAuth(context.Background(), first, seal); errCreate != nil {
		t.Fatalf("CreatePluginStoreAuth(first) error = %v", errCreate)
	}
	if errCreate := repo.CreatePluginStoreAuth(context.Background(), second, seal); errCreate != nil {
		t.Fatalf("CreatePluginStoreAuth(second) error = %v", errCreate)
	}
	records, errList := repo.ListPluginStoreAuth(context.Background())
	if errList != nil {
		t.Fatalf("ListPluginStoreAuth() error = %v", errList)
	}
	if len(records) != 2 {
		t.Fatalf("ListPluginStoreAuth() records = %d, want 2", len(records))
	}
	if records[0].ID != first.ID || records[1].ID != second.ID {
		t.Fatalf("ListPluginStoreAuth() IDs = %v, want %d,%d", []uint{records[0].ID, records[1].ID}, first.ID, second.ID)
	}
}

func TestUpdatePluginStoreAuthReturnsConflictSentinel(t *testing.T) {
	repo, _ := newPluginStoreAuthTestRepository(t)
	record := &PluginStoreAuthRecord{Name: "original", Match: "https://example.com/", AuthType: "none", Enabled: true}
	if errCreate := repo.CreatePluginStoreAuth(context.Background(), record, func(uint) ([]byte, int, error) {
		return nil, pluginStoreAuthKeyVersion, nil
	}); errCreate != nil {
		t.Fatalf("CreatePluginStoreAuth() error = %v", errCreate)
	}
	stale := *record
	record.Name = "updated"
	if errUpdate := repo.UpdatePluginStoreAuth(context.Background(), record); errUpdate != nil {
		t.Fatalf("UpdatePluginStoreAuth(current) error = %v", errUpdate)
	}
	stale.Name = "stale"
	if errUpdate := repo.UpdatePluginStoreAuth(context.Background(), &stale); !errors.Is(errUpdate, ErrPluginStoreAuthConflict) {
		t.Fatalf("UpdatePluginStoreAuth(stale) error = %v, want ErrPluginStoreAuthConflict", errUpdate)
	}
}

func newPluginStoreAuthTestRepository(t *testing.T) (*Repository, *gorm.DB) {
	t.Helper()
	db, errOpen := OpenSQLite(context.Background(), filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpen)
	}
	sqlDB, _ := db.DB()
	t.Cleanup(func() { _ = sqlDB.Close() })
	if errMigrate := AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	return NewRepository(db), db
}
