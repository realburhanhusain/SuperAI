package cluster

import (
	"bytes"
	"context"
	"log"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

func TestAppendEventSQLitePersistsEvent(t *testing.T) {
	db, errOpen := OpenSQLite(context.Background(), filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpen)
	}
	sqlDB, errDB := db.DB()
	if errDB != nil {
		t.Fatalf("db.DB() error = %v", errDB)
	}
	t.Cleanup(func() { _ = sqlDB.Close() })
	if errMigrate := db.AutoMigrate(&ClusterEventRecord{}); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}

	repo := NewRepository(db)
	if errAppend := repo.AppendEvent(context.Background(), "plugin-store-auth", "update", "1", 2); errAppend != nil {
		t.Fatalf("AppendEvent() error = %v", errAppend)
	}

	var event ClusterEventRecord
	if errFirst := db.First(&event).Error; errFirst != nil {
		t.Fatalf("load appended event: %v", errFirst)
	}
	if event.Scope != "plugin-store-auth" || event.Op != "update" || event.EntityUUID != "1" || event.Version != 2 {
		t.Fatalf("appended event = %#v", event)
	}
}

func TestLockClusterEventTransactionUsesPostgresAdvisoryLock(t *testing.T) {
	var logs bytes.Buffer
	db, errOpen := gorm.Open(postgres.New(postgres.Config{
		DSN:                  "host=127.0.0.1 user=cliproxy dbname=cliproxy_home sslmode=disable",
		PreferSimpleProtocol: true,
	}), &gorm.Config{
		DisableAutomaticPing: true,
		DryRun:               true,
		Logger: logger.New(log.New(&logs, "", 0), logger.Config{
			LogLevel: logger.Info,
		}),
	})
	if errOpen != nil {
		t.Fatalf("open postgres dry-run db: %v", errOpen)
	}

	if errLock := lockClusterEventTransaction(db); errLock != nil {
		t.Fatalf("lockClusterEventTransaction() error = %v", errLock)
	}
	output := logs.String()
	if !strings.Contains(output, "pg_advisory_xact_lock") || !strings.Contains(output, strconv.FormatInt(clusterEventAdvisoryLockKey, 10)) {
		t.Fatalf("postgres advisory lock SQL = %q", output)
	}
}
