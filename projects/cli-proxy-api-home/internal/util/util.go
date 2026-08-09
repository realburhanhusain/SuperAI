package util

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ResolveAuthDir normalizes the auth directory path for consistent reuse throughout the app.
// It expands a leading tilde (~) to the user's home directory and returns a cleaned path.
func ResolveAuthDir(authDir string) (string, error) {
	if authDir == "" {
		return "", nil
	}
	if strings.HasPrefix(authDir, "~") {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", fmt.Errorf("resolve auth dir: %w", err)
		}
		remainder := strings.TrimPrefix(authDir, "~")
		remainder = strings.TrimLeft(remainder, "/\\")
		if remainder == "" {
			return filepath.Clean(home), nil
		}
		normalized := strings.ReplaceAll(remainder, "\\", "/")
		return filepath.Clean(filepath.Join(home, filepath.FromSlash(normalized))), nil
	}
	return filepath.Clean(authDir), nil
}

// WritablePath returns the cleaned WRITABLE_PATH environment variable when it is set.
// It accepts both uppercase and lowercase variants for compatibility with existing conventions.
func WritablePath() string {
	for _, key := range []string{"WRITABLE_PATH", "writable_path"} {
		if value, ok := os.LookupEnv(key); ok {
			trimmed := strings.TrimSpace(value)
			if trimmed != "" {
				return filepath.Clean(trimmed)
			}
		}
	}
	return ""
}
