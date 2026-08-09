package push

import (
	"context"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/home"
	homelogging "github.com/router-for-me/CLIProxyAPIHome/internal/logging"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

func TestHandleAppLogPrintsAndStoresDatabaseWhenHomeLoggingToFile(t *testing.T) {
	t.Chdir(t.TempDir())

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

	rt, errRuntime := home.NewRuntime(&config.Config{LoggingToFile: true})
	if errRuntime != nil {
		t.Fatalf("NewRuntime: %v", errRuntime)
	}
	adapter := cluster.NewRuntimeAdapter(cluster.NewRepository(db), "192.0.2.10")
	rt.SetClusterAdapter(adapter)

	oldStdout := os.Stdout
	reader, writer, errPipe := os.Pipe()
	if errPipe != nil {
		t.Fatalf("pipe stdout: %v", errPipe)
	}
	os.Stdout = writer
	defer func() {
		os.Stdout = oldStdout
		_ = reader.Close()
	}()

	line := "[2026-05-29 08:00:00] [--------] [debug] debug details"
	timestamp := "2026-05-29T01:02:03Z"
	payload := `{"line":"` + line + `","level":"debug","timestamp":"` + timestamp + `","request_id":"req-app-1"}`
	reply := handleAppLog(ctx, dispatch.Env{ClientIP: "10.0.0.5", Runtime: rt}, []string{"RPUSH", "app-log", payload})
	if reply.Kind != dispatch.ReplyKindInteger || reply.Integer != 1 {
		t.Fatalf("reply = %+v, want integer 1", reply)
	}
	if errClose := writer.Close(); errClose != nil {
		t.Fatalf("close stdout writer: %v", errClose)
	}
	os.Stdout = oldStdout

	raw, errRead := io.ReadAll(reader)
	if errRead != nil {
		t.Fatalf("read stdout: %v", errRead)
	}
	got := strings.TrimSpace(string(raw))
	want := homelogging.FormatLogSourcePrefix("10.0.0.5") + " " + line
	if got != want {
		t.Fatalf("stdout = %q, want %q", got, want)
	}

	var records []cluster.AppLogRecord
	if errFind := db.Order("id").Find(&records).Error; errFind != nil {
		t.Fatalf("find app logs: %v", errFind)
	}
	if len(records) != 1 {
		t.Fatalf("app log records = %d, want 1", len(records))
	}
	if records[0].ClientIP != "10.0.0.5" {
		t.Fatalf("client ip = %q, want 10.0.0.5", records[0].ClientIP)
	}
	if records[0].RequestID != "req-app-1" {
		t.Fatalf("request id = %q, want req-app-1", records[0].RequestID)
	}
	if records[0].HomeIP != "192.0.2.10" {
		t.Fatalf("home ip = %q, want 192.0.2.10", records[0].HomeIP)
	}
	if records[0].Line != line {
		t.Fatalf("line = %q, want %q", records[0].Line, line)
	}
	if records[0].Level != "debug" {
		t.Fatalf("level = %q, want debug", records[0].Level)
	}
	if got := records[0].Timestamp.Format(time.RFC3339); got != timestamp {
		t.Fatalf("timestamp = %q, want %q", got, timestamp)
	}
	if _, errStat := os.Stat(filepath.Join("logs", "10.0.0.5-main.log")); !os.IsNotExist(errStat) {
		t.Fatalf("home app log file exists or stat failed: %v", errStat)
	}
}

func TestHandleAppLogPrintsCPAConsolePrefixWhenHomeLoggingToConsole(t *testing.T) {
	t.Chdir(t.TempDir())

	oldStdout := os.Stdout
	reader, writer, errPipe := os.Pipe()
	if errPipe != nil {
		t.Fatalf("pipe stdout: %v", errPipe)
	}
	os.Stdout = writer
	defer func() {
		os.Stdout = oldStdout
		_ = reader.Close()
	}()

	line := "[2026-05-29 08:00:00] [--------] [debug] debug details"
	payload := `{"line":"` + line + `","level":"debug","timestamp":"2026-05-29T01:02:03Z"}`
	reply := handleAppLog(context.Background(), dispatch.Env{ClientIP: "10.0.0.8"}, []string{"RPUSH", "app-log", payload})
	if reply.Kind != dispatch.ReplyKindInteger || reply.Integer != 1 {
		t.Fatalf("reply = %+v, want integer 1", reply)
	}
	if errClose := writer.Close(); errClose != nil {
		t.Fatalf("close stdout writer: %v", errClose)
	}
	os.Stdout = oldStdout

	raw, errRead := io.ReadAll(reader)
	if errRead != nil {
		t.Fatalf("read stdout: %v", errRead)
	}
	got := strings.TrimSpace(string(raw))
	want := homelogging.FormatLogSourcePrefix("10.0.0.8") + " " + line
	if got != want {
		t.Fatalf("stdout = %q, want %q", got, want)
	}
}
