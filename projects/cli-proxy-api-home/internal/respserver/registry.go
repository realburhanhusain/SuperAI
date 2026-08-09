package respserver

import (
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
	respget "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/get"
	respkv "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/kv"
	resppop "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/pop"
	resppush "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/push"
	respset "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/set"
	respsubscribe "github.com/router-for-me/CLIProxyAPIHome/internal/respserver/subscribe"
)

const clusterCommand = "CLUSTER"
const configSubscriptionChannel = "config"
const clusterSubscriptionChannel = "cluster"

// buildRegistry builds a registry.
func buildRegistry() *dispatch.Registry {
	reg := dispatch.NewRegistry()
	respset.Register(reg)
	respkv.Register(reg)
	respget.Register(reg)
	respsubscribe.Register(reg)
	resppush.Register(reg)
	resppop.Register(reg)
	return reg
}
