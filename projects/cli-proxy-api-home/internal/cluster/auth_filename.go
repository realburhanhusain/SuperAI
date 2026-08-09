package cluster

import (
	"path/filepath"
	"strings"

	coreauth "github.com/router-for-me/CLIProxyAPIHome/internal/cliproxy/auth"
)

// ApplyOriginalAuthFileName stores the source OAuth file name for management display.
func ApplyOriginalAuthFileName(auths []*coreauth.Auth, filename string) {
	displayName := normalizeOriginalAuthFileName(filename)
	if displayName == "" {
		return
	}
	for _, auth := range auths {
		if auth == nil {
			continue
		}
		if auth.Metadata == nil {
			auth.Metadata = make(map[string]any)
		}
		auth.Metadata["filename"] = displayName
	}
}

// normalizeOriginalAuthFileName normalizes an original auth file name.
func normalizeOriginalAuthFileName(filename string) string {
	filename = strings.TrimSpace(filename)
	if filename == "" {
		return ""
	}
	filename = strings.ReplaceAll(filename, "\\", "/")
	filename = filepath.Base(filename)
	if filename == "." || filename == "/" {
		return ""
	}
	if !strings.HasSuffix(strings.ToLower(filename), ".json") {
		return ""
	}
	return filename
}
