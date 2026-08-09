package cluster

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
)

func TestReplacePluginStatusStoresLatestPerNodePluginRows(t *testing.T) {
	ctx := context.Background()
	db, errOpen := OpenSQLite(ctx, filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite: %v", errOpen)
	}
	sqlDB, errDB := db.DB()
	if errDB != nil {
		t.Fatalf("DB: %v", errDB)
	}
	defer func() {
		if errClose := sqlDB.Close(); errClose != nil {
			t.Errorf("close db: %v", errClose)
		}
	}()
	if errMigrate := AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate: %v", errMigrate)
	}

	repo := NewRepository(db)
	first := node.PluginTaskStatus{
		SchemaVersion: 1,
		Task:          "plugin-sync",
		NodeID:        "node-1",
		ClientIP:      "10.0.0.5",
		Status:        "failed",
		Phase:         "install",
		OK:            false,
		StartedAt:     time.Now().UTC(),
		UpdatedAt:     time.Now().UTC(),
		Platform:      node.PluginTaskPlatform{GOOS: "linux", GOARCH: "amd64"},
		Plugins: []node.PluginTaskPlugin{
			{ID: "alpha", Version: "0.1.0", InstallStatus: "installed", LoadStatus: "loaded"},
			{ID: "bravo", Version: "0.2.0", InstallStatus: "failed", Error: "boom"},
		},
		Error: "boom",
	}
	if errStore := repo.ReplacePluginStatus(ctx, node.PluginStatusNodeTypeCPA, first); errStore != nil {
		t.Fatalf("ReplacePluginStatus(first) error = %v", errStore)
	}

	second := first
	second.Status = "success"
	second.Phase = "load"
	second.OK = true
	second.Error = ""
	second.UpdatedAt = time.Now().UTC()
	second.Plugins = []node.PluginTaskPlugin{
		{ID: "bravo", Version: "0.2.1", InstallStatus: "installed", LoadStatus: "loaded"},
	}
	if errStore := repo.ReplacePluginStatus(ctx, node.PluginStatusNodeTypeCPA, second); errStore != nil {
		t.Fatalf("ReplacePluginStatus(second) error = %v", errStore)
	}

	statuses, errList := repo.ListPluginStatuses(ctx, node.PluginStatusNodeTypeCPA)
	if errList != nil {
		t.Fatalf("ListPluginStatuses() error = %v", errList)
	}
	if len(statuses) != 1 {
		t.Fatalf("ListPluginStatuses() len = %d, want 1", len(statuses))
	}
	got := statuses[0]
	if got.NodeType != node.PluginStatusNodeTypeCPA || got.NodeID != "node-1" || !got.OK || got.Status != "success" || got.Phase != "load" {
		t.Fatalf("status = %+v, want latest successful cpa status", got)
	}
	if len(got.Plugins) != 1 || got.Plugins[0].ID != "bravo" || got.Plugins[0].Version != "0.2.1" {
		t.Fatalf("plugins = %+v, want latest bravo only", got.Plugins)
	}
}

func TestReplacePluginStatusPreservesOtherRowsForDeleteReports(t *testing.T) {
	ctx := context.Background()
	db, errOpen := OpenSQLite(ctx, filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite: %v", errOpen)
	}
	sqlDB, errDB := db.DB()
	if errDB != nil {
		t.Fatalf("DB: %v", errDB)
	}
	defer func() {
		if errClose := sqlDB.Close(); errClose != nil {
			t.Errorf("close db: %v", errClose)
		}
	}()
	if errMigrate := AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate: %v", errMigrate)
	}

	repo := NewRepository(db)
	now := time.Now().UTC()
	fullStatus := node.PluginTaskStatus{
		SchemaVersion: 1,
		Task:          "plugin-sync",
		NodeID:        "node-1",
		Status:        "success",
		Phase:         "load",
		OK:            true,
		StartedAt:     now,
		UpdatedAt:     now,
		Platform:      node.PluginTaskPlatform{GOOS: "linux", GOARCH: "amd64"},
		Plugins: []node.PluginTaskPlugin{
			{ID: "alpha", Version: "0.1.0", InstallStatus: "installed", LoadStatus: "loaded"},
			{ID: "bravo", Version: "0.2.0", InstallStatus: "installed", LoadStatus: "loaded"},
		},
	}
	if errStore := repo.ReplacePluginStatus(ctx, node.PluginStatusNodeTypeCPA, fullStatus); errStore != nil {
		t.Fatalf("ReplacePluginStatus(full) error = %v", errStore)
	}

	deleteStatus := node.PluginTaskStatus{
		SchemaVersion: 1,
		TaskID:        42,
		Task:          "plugin-delete",
		NodeID:        "node-1",
		Status:        "success",
		Phase:         "delete",
		OK:            true,
		StartedAt:     now.Add(time.Second),
		UpdatedAt:     now.Add(time.Second),
		Platform:      node.PluginTaskPlatform{GOOS: "linux", GOARCH: "amd64"},
		Plugins: []node.PluginTaskPlugin{
			{ID: "alpha", InstallStatus: "deleted"},
		},
	}
	if errStore := repo.ReplacePluginStatus(ctx, node.PluginStatusNodeTypeCPA, deleteStatus); errStore != nil {
		t.Fatalf("ReplacePluginStatus(delete) error = %v", errStore)
	}

	statuses, errList := repo.ListPluginStatuses(ctx, node.PluginStatusNodeTypeCPA)
	if errList != nil {
		t.Fatalf("ListPluginStatuses() error = %v", errList)
	}
	if len(statuses) != 2 {
		t.Fatalf("ListPluginStatuses() len = %d, want 2", len(statuses))
	}

	var deleteReport *node.PluginTaskStatus
	var syncReport *node.PluginTaskStatus
	for i := range statuses {
		switch statuses[i].Task {
		case "plugin-delete":
			deleteReport = &statuses[i]
		case "plugin-sync":
			syncReport = &statuses[i]
		}
	}
	if deleteReport == nil {
		t.Fatalf("delete report missing from statuses: %+v", statuses)
	}
	if syncReport == nil {
		t.Fatalf("sync report missing from statuses: %+v", statuses)
	}
	if len(deleteReport.Plugins) != 1 || deleteReport.Plugins[0].ID != "alpha" || deleteReport.Plugins[0].InstallStatus != "deleted" {
		t.Fatalf("delete report plugins = %+v, want deleted alpha only", deleteReport.Plugins)
	}
	if len(syncReport.Plugins) != 1 || syncReport.Plugins[0].ID != "bravo" || syncReport.Plugins[0].Version != "0.2.0" || syncReport.Plugins[0].InstallStatus != "installed" {
		t.Fatalf("sync report plugins = %+v, want preserved installed bravo only", syncReport.Plugins)
	}
}
