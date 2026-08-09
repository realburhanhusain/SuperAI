package logging

import (
	"context"
)

// requestIDKey is the context key for storing/retrieving request IDs.
type requestIDKey struct{}

// GetRequestID retrieves the request ID from the context.
// Returns empty string if not found.
func GetRequestID(ctx context.Context) string {
	if ctx == nil {
		return ""
	}
	if id, ok := ctx.Value(requestIDKey{}).(string); ok {
		return id
	}
	return ""
}
