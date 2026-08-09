package get

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

func handlePluginTasks(ctx context.Context, env dispatch.Env, args []string) dispatch.Reply {
	if env.Runtime == nil {
		return dispatch.Err("runtime not ready")
	}
	if len(args) != 2 {
		return dispatch.Err("wrong number of arguments for 'get' command")
	}
	nodeID := strings.TrimSpace(env.NodeID)
	if nodeID == "" {
		return dispatch.Err("plugin task node_id is required")
	}
	if ctx == nil {
		ctx = context.Background()
	}
	tasks, errTasks := env.Runtime.ListPendingPluginTasks(ctx, node.PluginStatusNodeTypeCPA, nodeID)
	if errTasks != nil {
		return dispatch.Err(errTasks.Error())
	}
	raw, errMarshal := json.Marshal(tasks)
	if errMarshal != nil {
		return dispatch.Err(errMarshal.Error())
	}
	return dispatch.BulkString(raw)
}
