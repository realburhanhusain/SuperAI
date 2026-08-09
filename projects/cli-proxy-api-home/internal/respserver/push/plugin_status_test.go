package push

import (
	"context"
	"path/filepath"
	"strings"
	"testing"

	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/home"
	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

func TestHandlePluginStatusStoresRecordWithClientIP(t *testing.T) {
	ctx := context.Background()
	db, errOpen := cluster.OpenSQLite(ctx, filepath.Join(t.TempDir(), "home.db"))
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
	if errMigrate := cluster.AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate: %v", errMigrate)
	}

	repo := cluster.NewRepository(db)
	rt, errRuntime := home.NewRuntime(&config.Config{})
	if errRuntime != nil {
		t.Fatalf("NewRuntime: %v", errRuntime)
	}
	rt.SetClusterAdapter(cluster.NewRuntimeAdapter(repo, "192.0.2.10"))

	payload := `{"schema_version":1,"task":"plugin-sync","node_id":"node-1","status":"failed","phase":"install","ok":false,"plugins":[{"id":"sample","install_status":"failed","error":"boom"}]}`
	reply := handlePluginStatus(ctx, dispatch.Env{ClientIP: "10.0.0.5", Runtime: rt}, []string{"RPUSH", "plugin-status", payload})
	if reply.Kind != dispatch.ReplyKindInteger || reply.Integer != 1 {
		t.Fatalf("reply = %+v, want integer 1", reply)
	}

	statuses, errList := repo.ListPluginStatuses(ctx, node.PluginStatusNodeTypeCPA)
	if errList != nil {
		t.Fatalf("ListPluginStatuses() error = %v", errList)
	}
	if len(statuses) != 1 {
		t.Fatalf("ListPluginStatuses() len = %d, want 1", len(statuses))
	}
	stored := statuses[0]
	if stored.NodeID != "node-1" || stored.ClientIP != "10.0.0.5" || stored.OK {
		t.Fatalf("stored status = %+v, want node id, client ip, failed ok", stored)
	}
	if stored.NodeType != node.PluginStatusNodeTypeCPA || len(stored.Plugins) != 1 || stored.Plugins[0].ID != "sample" {
		t.Fatalf("stored plugins = %+v, want cpa sample status", stored)
	}

	mismatchReply := handlePluginStatus(ctx, dispatch.Env{ClientIP: "10.0.0.5", NodeID: "node-2", Runtime: rt}, []string{"RPUSH", "plugin-status", payload})
	if mismatchReply.Kind != dispatch.ReplyKindRedisError || !strings.Contains(mismatchReply.RedisError, "node_id does not match") {
		t.Fatalf("mismatch reply = %+v, want node_id mismatch error", mismatchReply)
	}
}
