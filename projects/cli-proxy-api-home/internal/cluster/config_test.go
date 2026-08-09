package cluster

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadConfigOptionalParsesExternalPort(t *testing.T) {
	t.Parallel()

	configPath := filepath.Join(t.TempDir(), "cluster.yaml")
	content := strings.TrimSpace(`
pgsql:
  host: "127.0.0.1"
  port: 5432
  user: "cliproxy"
  password: "secret"
  database: "cliproxy_home"
node:
  external-ip: "203.0.113.10"
  external-port: 443
  port: 8327
`) + "\n"
	if errWrite := os.WriteFile(configPath, []byte(content), 0o600); errWrite != nil {
		t.Fatalf("write config: %v", errWrite)
	}

	cfg, exists, errLoad := LoadConfigOptional(configPath)
	if errLoad != nil {
		t.Fatalf("LoadConfigOptional failed: %v", errLoad)
	}
	if !exists {
		t.Fatalf("expected config to exist")
	}
	if cfg.Node.ExternalIP != "203.0.113.10" {
		t.Fatalf("external ip = %q, want %q", cfg.Node.ExternalIP, "203.0.113.10")
	}
	if cfg.Node.ExternalPort != 443 {
		t.Fatalf("external port = %d, want 443", cfg.Node.ExternalPort)
	}
}

func TestLoadConfigOptional_RejectsBothPGSQLAndSQLite(t *testing.T) {
	t.Parallel()

	configPath := filepath.Join(t.TempDir(), "cluster.yaml")
	content := strings.TrimSpace(`
pgsql:
  host: "127.0.0.1"
  port: 5432
  user: "cliproxy"
  password: "secret"
  database: "cliproxy_home"
sqlite:
  path: "home.db"
node:
  port: 8327
`) + "\n"
	if errWrite := os.WriteFile(configPath, []byte(content), 0o600); errWrite != nil {
		t.Fatalf("write config: %v", errWrite)
	}

	_, exists, errLoad := LoadConfigOptional(configPath)
	if errLoad == nil {
		t.Fatalf("expected validation error")
	}
	if !exists {
		t.Fatalf("expected config to exist")
	}
	if !strings.Contains(errLoad.Error(), "exactly one database backend") {
		t.Fatalf("unexpected validation error: %v", errLoad)
	}
}

func TestConfigValidateRejectsNegativeExternalPort(t *testing.T) {
	t.Parallel()

	cfg := &Config{
		PGSQL: PGSQLConfig{
			Host:     "127.0.0.1",
			Port:     5432,
			User:     "cliproxy",
			Database: "cliproxy_home",
		},
		Node: NodeConfig{
			ExternalPort:      -1,
			Port:              8327,
			HeartbeatInterval: defaultHeartbeatInterval,
			HeartbeatTimeout:  defaultHeartbeatTimeout,
			EventPollInterval: defaultHeartbeatInterval,
		},
	}

	errValidate := cfg.Validate()
	if errValidate == nil {
		t.Fatalf("expected validation error")
	}
	if !strings.Contains(errValidate.Error(), "node.external-port") {
		t.Fatalf("unexpected validation error: %v", errValidate)
	}
}
