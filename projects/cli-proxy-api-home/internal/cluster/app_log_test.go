package cluster

import (
	"testing"
	"time"
)

func TestAppLogRecordFromPayloadStoresLineLevelAndTimestamp(t *testing.T) {
	line := "[2026-05-29 08:00:00] [req-123] [warn ] [manager.go:524] Use API key provider=codex model=gpt-5"
	payload := `{"line":"` + line + `","level":"warning","timestamp":"2026-05-29T01:02:03Z","request_id":"req-123"}`

	record, errRecord := AppLogRecordFromPayload("10.0.0.5", "192.0.2.10", payload)
	if errRecord != nil {
		t.Fatalf("AppLogRecordFromPayload: %v", errRecord)
	}

	if record.ClientIP != "10.0.0.5" {
		t.Fatalf("client ip = %q, want 10.0.0.5", record.ClientIP)
	}
	if record.Line != line {
		t.Fatalf("line = %q, want %q", record.Line, line)
	}
	if record.RequestID != "req-123" {
		t.Fatalf("request id = %q, want req-123", record.RequestID)
	}
	if record.HomeIP != "192.0.2.10" {
		t.Fatalf("home ip = %q, want 192.0.2.10", record.HomeIP)
	}
	if record.Level != "warn" {
		t.Fatalf("level = %q, want warn", record.Level)
	}
	if got := record.Timestamp.Format(time.RFC3339); got != "2026-05-29T01:02:03Z" {
		t.Fatalf("timestamp = %q, want 2026-05-29T01:02:03Z", got)
	}
	if record.CreatedAt.IsZero() {
		t.Fatal("created at is zero, want receive timestamp")
	}
}

func TestAppLogRecordFromPayloadRequiresLine(t *testing.T) {
	payload := `{"message":"payload message"}`
	record, errRecord := AppLogRecordFromPayload("", "", payload)
	if errRecord == nil {
		t.Fatalf("AppLogRecordFromPayload record = %+v, want error", record)
	}
}
