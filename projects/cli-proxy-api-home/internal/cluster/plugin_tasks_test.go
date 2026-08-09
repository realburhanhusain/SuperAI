package cluster

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
)

func TestPluginTasksArePendingUntilNodeAck(t *testing.T) {
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
	globalTask, errCreate := repo.CreatePluginTask(ctx, node.PluginTask{
		Operation: node.PluginTaskOperationDelete,
		PluginID:  "sample",
	})
	if errCreate != nil {
		t.Fatalf("CreatePluginTask(global) error = %v", errCreate)
	}
	targetTask, errCreate := repo.CreatePluginTask(ctx, node.PluginTask{
		Operation:    node.PluginTaskOperationDelete,
		PluginID:     "target-only",
		TargetNodeID: "node-2",
	})
	if errCreate != nil {
		t.Fatalf("CreatePluginTask(target) error = %v", errCreate)
	}

	tasks, errList := repo.ListPendingPluginTasks(ctx, node.PluginStatusNodeTypeCPA, "node-1")
	if errList != nil {
		t.Fatalf("ListPendingPluginTasks(node-1) error = %v", errList)
	}
	if len(tasks) != 1 || tasks[0].ID != globalTask.ID {
		t.Fatalf("node-1 tasks = %+v, want global task only", tasks)
	}

	tasks, errList = repo.ListPendingPluginTasks(ctx, node.PluginStatusNodeTypeCPA, "node-2")
	if errList != nil {
		t.Fatalf("ListPendingPluginTasks(node-2) error = %v", errList)
	}
	if len(tasks) != 2 || tasks[0].ID != globalTask.ID || tasks[1].ID != targetTask.ID {
		t.Fatalf("node-2 tasks = %+v, want global and targeted tasks", tasks)
	}

	now := time.Now().UTC()
	if errStore := repo.ReplacePluginStatus(ctx, node.PluginStatusNodeTypeCPA, node.PluginTaskStatus{
		SchemaVersion: 1,
		TaskID:        globalTask.ID,
		Task:          "plugin-delete",
		NodeID:        "node-1",
		Status:        "success",
		Phase:         "delete",
		OK:            true,
		StartedAt:     now,
		UpdatedAt:     now,
		Platform:      node.PluginTaskPlatform{GOOS: "linux", GOARCH: "amd64"},
		Plugins: []node.PluginTaskPlugin{{
			ID:            "sample",
			InstallStatus: "deleted",
		}},
	}); errStore != nil {
		t.Fatalf("ReplacePluginStatus(delete ack) error = %v", errStore)
	}
	tasks, errList = repo.ListPendingPluginTasks(ctx, node.PluginStatusNodeTypeCPA, "node-1")
	if errList != nil {
		t.Fatalf("ListPendingPluginTasks(node-1 after ack) error = %v", errList)
	}
	if len(tasks) != 0 {
		t.Fatalf("node-1 tasks after ack = %+v, want none", tasks)
	}

	if errStore := repo.ReplacePluginStatus(ctx, node.PluginStatusNodeTypeCPA, node.PluginTaskStatus{
		SchemaVersion: 1,
		Task:          "plugin-sync",
		NodeID:        "node-1",
		Status:        "success",
		Phase:         "load",
		OK:            true,
		StartedAt:     now.Add(time.Second),
		UpdatedAt:     now.Add(time.Second),
		Platform:      node.PluginTaskPlatform{GOOS: "linux", GOARCH: "amd64"},
		Plugins:       []node.PluginTaskPlugin{},
	}); errStore != nil {
		t.Fatalf("ReplacePluginStatus(sync after ack) error = %v", errStore)
	}
	tasks, errList = repo.ListPendingPluginTasks(ctx, node.PluginStatusNodeTypeCPA, "node-1")
	if errList != nil {
		t.Fatalf("ListPendingPluginTasks(node-1 after sync) error = %v", errList)
	}
	if len(tasks) != 0 {
		t.Fatalf("node-1 tasks after sync = %+v, want ack to remain", tasks)
	}
}
