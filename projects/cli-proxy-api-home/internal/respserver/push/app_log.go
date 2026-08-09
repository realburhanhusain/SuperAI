package push

import (
	"context"
	"fmt"
	"os"
	"strings"

	homelogging "github.com/router-for-me/CLIProxyAPIHome/internal/logging"
	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
	log "github.com/sirupsen/logrus"
	"github.com/tidwall/gjson"
)

// handleAppLog handles a CPA application log line.
func handleAppLog(ctx context.Context, env dispatch.Env, args []string) dispatch.Reply {
	if len(args) != 3 {
		return dispatch.Err("wrong number of arguments for 'rpush' command")
	}

	if !strings.EqualFold(strings.TrimSpace(args[1]), "app-log") {
		return dispatch.Err("unsupported key")
	}

	payload := strings.TrimSpace(args[2])
	if payload == "" || !gjson.Valid(payload) {
		return dispatch.Err("invalid app-log json")
	}

	line := strings.TrimRight(gjson.Get(payload, "line").String(), "\r\n")
	if strings.TrimSpace(line) == "" {
		return dispatch.Err("missing line")
	}

	clientIP := strings.TrimSpace(env.ClientIP)
	if clientIP == "" {
		clientIP = "unknown"
	}

	writeAppLogConsole(clientIP, line)

	if env.Runtime != nil {
		persisted, errPersist := env.Runtime.PersistAppLogPayload(ctx, clientIP, payload)
		if errPersist != nil {
			log.Errorf("app log database write error: %v", errPersist)
			return dispatch.Err("app log database write failed")
		}
		if persisted {
			return dispatch.Integer(1)
		}
	}

	return dispatch.Integer(1)
}

func writeAppLogConsole(clientIP string, line string) {
	clientIP = strings.TrimSpace(clientIP)
	if clientIP == "" {
		clientIP = "unknown"
	}
	line = strings.TrimRight(line, "\r\n")
	if strings.TrimSpace(line) == "" {
		return
	}

	prefix := homelogging.FormatLogSourcePrefix(clientIP) + " "
	for _, part := range strings.Split(line, "\n") {
		part = strings.TrimRight(part, "\r")
		if strings.TrimSpace(part) == "" {
			continue
		}
		_, _ = fmt.Fprintln(os.Stdout, prefix+part)
	}
}
