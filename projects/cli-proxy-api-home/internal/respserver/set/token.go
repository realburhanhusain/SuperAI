package set

import (
	"context"

	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

// handleToken converts handle token.
func handleToken(ctx context.Context, env dispatch.Env, args []string) dispatch.Reply {
	if env.Runtime == nil {
		return dispatch.Err("runtime not ready")
	}
	if ctx == nil {
		ctx = context.Background()
	}

	if len(args) != 3 {
		return dispatch.Err("wrong number of arguments for 'set' command")
	}

	_, errAdd := env.Runtime.AddToken(ctx, args[2])
	if errAdd != nil {
		return dispatch.Err(errAdd.Error())
	}
	return dispatch.SimpleString("OK")
}
