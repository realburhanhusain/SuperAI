package subscribe

import "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"

// Register wires package handlers into the provided registry.
func Register(reg *dispatch.Registry) {
	if reg == nil {
		return
	}
	_ = reg.RegisterDirect("SUBSCRIBE", "config", handleConfig)
}
