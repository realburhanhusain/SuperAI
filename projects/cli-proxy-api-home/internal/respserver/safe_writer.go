package respserver

import (
	"bufio"
	"io"
	"net"
	"sync"

	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

type safeWriter struct {
	mu  sync.Mutex
	raw io.Writer
	w   *bufio.Writer
}

// newSafeWriter creates a safe writer.
func newSafeWriter(w io.Writer) *safeWriter {
	if w == nil {
		return &safeWriter{}
	}
	return &safeWriter{raw: w, w: bufio.NewWriter(w)}
}

// WriteDispatchReply writes a dispatch reply.
func (w *safeWriter) WriteDispatchReply(reply dispatch.Reply) error {
	defer reply.ClearSensitive()
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.w == nil {
		return net.ErrClosed
	}
	if replyContainsSensitive(reply) {
		if errFlush := w.w.Flush(); errFlush != nil {
			return errFlush
		}
		return writeDispatchReply(directRESPWriter{writer: w.raw}, reply)
	}
	if errWrite := writeDispatchReply(w.w, reply); errWrite != nil {
		return errWrite
	}
	return w.w.Flush()
}

func replyContainsSensitive(reply dispatch.Reply) bool {
	if reply.Sensitive {
		return true
	}
	for _, entry := range reply.Array {
		if replyContainsSensitive(entry) {
			return true
		}
	}
	return false
}

type directRESPWriter struct {
	writer io.Writer
}

func (w directRESPWriter) Write(payload []byte) (int, error) {
	if w.writer == nil {
		return 0, net.ErrClosed
	}
	total := 0
	for len(payload) > 0 {
		count, errWrite := w.writer.Write(payload)
		if count < 0 || count > len(payload) {
			return total, io.ErrShortWrite
		}
		total += count
		payload = payload[count:]
		if errWrite != nil {
			return total, errWrite
		}
		if count == 0 {
			return total, io.ErrShortWrite
		}
	}
	return total, nil
}

func (w directRESPWriter) WriteString(value string) (int, error) {
	return w.Write([]byte(value))
}

// WriteRedisSimpleString writes a redis simple string.
func (w *safeWriter) WriteRedisSimpleString(value string) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.w == nil {
		return net.ErrClosed
	}
	if errWrite := writeRedisSimpleString(w.w, value); errWrite != nil {
		return errWrite
	}
	return w.w.Flush()
}

// WriteRedisError writes a redis error.
func (w *safeWriter) WriteRedisError(message string) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.w == nil {
		return net.ErrClosed
	}
	if errWrite := writeRedisError(w.w, message); errWrite != nil {
		return errWrite
	}
	return w.w.Flush()
}

// WriteRedisBulkString writes a redis bulk string.
func (w *safeWriter) WriteRedisBulkString(payload []byte) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.w == nil {
		return net.ErrClosed
	}
	if errWrite := writeRedisBulkString(w.w, payload); errWrite != nil {
		return errWrite
	}
	return w.w.Flush()
}
