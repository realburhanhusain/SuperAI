package respserver

import (
	"bytes"
	"strings"
	"testing"

	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

func TestSafeWriterClearsSensitiveBulkStringAfterWrite(t *testing.T) {
	var output bytes.Buffer
	payload := []byte("sensitive-payload")
	backing := payload
	writer := newSafeWriter(&output)
	if errWrite := writer.WriteDispatchReply(dispatch.SensitiveBulkString(payload)); errWrite != nil {
		t.Fatalf("WriteDispatchReply() error = %v", errWrite)
	}
	if !strings.Contains(output.String(), "sensitive-payload") {
		t.Fatalf("wire output = %q, want payload", output.String())
	}
	for index, value := range backing {
		if value != 0 {
			t.Fatalf("payload byte %d = %d, want zero", index, value)
		}
	}
	bufferBacking := writer.w.AvailableBuffer()
	bufferBacking = bufferBacking[:cap(bufferBacking)]
	if bytes.Contains(bufferBacking, []byte("sensitive-payload")) {
		t.Fatal("persistent response buffer retained sensitive payload")
	}
}
