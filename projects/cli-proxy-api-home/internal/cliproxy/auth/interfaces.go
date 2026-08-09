package auth

import (
	"context"
	"net/http"
)

// Selector chooses an auth candidate for dispatch.
type Selector interface {
	Pick(ctx context.Context, provider, model string, opts Options, auths []*Auth) (*Auth, error)
}

// StoppableSelector is an optional interface for selectors that hold resources.
// Selectors that implement this interface will have Stop called during shutdown.
type StoppableSelector interface {
	Selector
	Stop()
}

// RoundTripperProvider defines a minimal provider of per-auth HTTP transports.
type RoundTripperProvider interface {
	RoundTripperFor(auth *Auth) http.RoundTripper
}
