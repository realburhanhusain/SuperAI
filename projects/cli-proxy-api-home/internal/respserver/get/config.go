package get

import (
	"context"

	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

// handleConfig handles a config.
func handleConfig(ctx context.Context, env dispatch.Env, args []string) dispatch.Reply {
	_ = ctx

	if env.Runtime == nil {
		return dispatch.Err("runtime not ready")
	}

	if len(args) != 2 {
		return dispatch.Err("wrong number of arguments for 'get' command")
	}

	data, errRead := env.Runtime.ReadConfigYAMLContext(ctx)
	if errRead != nil {
		return dispatch.Err(errRead.Error())
	}
	return dispatch.BulkString(data)
}
