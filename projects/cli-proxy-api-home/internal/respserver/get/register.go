package get

import "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"

// Register wires package handlers into the provided registry.
func Register(reg *dispatch.Registry) {
	if reg == nil {
		return
	}
	_ = reg.RegisterDirect("GET", "config", handleConfig)
	_ = reg.RegisterDirect("GET", "plugin-tasks", handlePluginTasks)
	_ = reg.RegisterDirect("GET", "plugin-sync", handlePluginSync)
	_ = reg.SetDirectDefault("GET", handleDefault)
}
