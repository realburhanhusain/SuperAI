package get

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/router-for-me/CLIProxyAPI/v7/sdk/pluginstore"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

func handlePluginSync(ctx context.Context, env dispatch.Env, args []string) dispatch.Reply {
	if env.Runtime == nil {
		return dispatch.Err("runtime not ready")
	}
	if len(args) != 3 {
		return dispatch.Err("wrong number of arguments for 'get' command")
	}
	nodeID := strings.TrimSpace(env.NodeID)
	fingerprint := strings.TrimSpace(env.ClientCertificateFingerprint)
	if nodeID == "" || fingerprint == "" {
		return dispatch.Err("plugin sync requires mTLS node identity")
	}
	active, errActive := env.Runtime.PluginSyncNodeActive(ctx, nodeID, fingerprint)
	if errActive != nil {
		return dispatch.Err(errActive.Error())
	}
	if !active {
		return dispatch.Err("plugin sync client certificate is revoked or unknown")
	}
	var request pluginstore.PluginSyncRequest
	if errDecode := json.Unmarshal([]byte(args[2]), &request); errDecode != nil {
		return dispatch.Err("invalid plugin sync request")
	}
	defer request.Clear()
	response, errBuild := env.Runtime.BuildPluginSyncPlan(ctx, request)
	if errBuild != nil {
		return dispatch.Err(errBuild.Error())
	}
	defer response.Clear()
	raw, errMarshal := marshalPluginSyncResponse(response)
	if errMarshal != nil {
		return dispatch.Err(errMarshal.Error())
	}
	return dispatch.SensitiveBulkString(raw)
}
