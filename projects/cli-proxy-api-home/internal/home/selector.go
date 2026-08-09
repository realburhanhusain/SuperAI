package home

import (
	"strings"
	"time"

	coreauth "github.com/router-for-me/CLIProxyAPIHome/internal/cliproxy/auth"
	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
)

// selectorFromConfig derives selector from config.
func selectorFromConfig(cfg *config.Config) coreauth.Selector {
	// Build the candidate view before applying availability rules.
	if cfg == nil {
		return &coreauth.RoundRobinSelector{}
	}

	strategy := strings.ToLower(strings.TrimSpace(cfg.Routing.Strategy))
	var selector coreauth.Selector
	switch strategy {
	case "fill-first", "fillfirst", "ff":
		selector = &coreauth.FillFirstSelector{}
	default:
		selector = &coreauth.RoundRobinSelector{}
	}

	sessionAffinity := cfg.Routing.ClaudeCodeSessionAffinity || cfg.Routing.SessionAffinity
	if !sessionAffinity {
		return selector
	}

	ttl := time.Hour
	if ttlStr := strings.TrimSpace(cfg.Routing.SessionAffinityTTL); ttlStr != "" {
		if parsed, errParse := time.ParseDuration(ttlStr); errParse == nil && parsed > 0 {
			ttl = parsed
		}
	}

	return coreauth.NewSessionAffinitySelectorWithConfig(coreauth.SessionAffinityConfig{
		Fallback: selector,
		TTL:      ttl,
	})
}
