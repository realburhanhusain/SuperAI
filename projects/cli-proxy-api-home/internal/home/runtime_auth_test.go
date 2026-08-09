package home

import (
	"context"
	"net/http"
	"testing"

	"github.com/router-for-me/CLIProxyAPIHome/internal/access"
)

func TestRuntimeAuthenticateRequestFailClosedWithoutAccessManager(t *testing.T) {
	rt := &Runtime{}
	_, authErr := rt.authenticateRequest(context.Background(), http.Header{})
	if !access.IsAuthErrorCode(authErr, access.AuthErrorCodeNoCredentials) {
		t.Fatalf("authenticateRequest() error = %v, want no credentials", authErr)
	}
}
