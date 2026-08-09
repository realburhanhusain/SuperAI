package push

import (
	"context"
	"encoding/json"
	"strings"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

func handlePluginStatus(ctx context.Context, env dispatch.Env, args []string) dispatch.Reply {
	if env.Runtime == nil {
		return dispatch.Err("runtime not ready")
	}
	if len(args) != 3 {
		return dispatch.Err("wrong number of arguments for 'rpush' command")
	}
	if ctx == nil {
		ctx = context.Background()
	}
	var status node.PluginTaskStatus
	if errUnmarshal := json.Unmarshal([]byte(args[2]), &status); errUnmarshal != nil {
		return dispatch.Err("invalid plugin status payload")
	}
	status.NodeID = strings.TrimSpace(status.NodeID)
	certNodeID := strings.TrimSpace(env.NodeID)
	if certNodeID != "" {
		if status.NodeID != "" && status.NodeID != certNodeID {
			return dispatch.Err("plugin status node_id does not match client certificate")
		}
		status.NodeID = certNodeID
	}
	if status.NodeID == "" {
		return dispatch.Err("plugin status node_id is required")
	}
	if strings.TrimSpace(env.ClientIP) != "" {
		status.ClientIP = strings.TrimSpace(env.ClientIP)
	}
	now := time.Now().UTC()
	if status.UpdatedAt.IsZero() {
		status.UpdatedAt = now
	}
	if errStore := env.Runtime.ReplacePluginStatus(ctx, node.PluginStatusNodeTypeCPA, status); errStore != nil {
		return dispatch.Err(errStore.Error())
	}
	return dispatch.Integer(1)
}
