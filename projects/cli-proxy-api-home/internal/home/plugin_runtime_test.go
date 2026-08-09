package home

import (
	"path/filepath"
	"testing"

	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"gopkg.in/yaml.v3"
)

func TestPluginRuntimeConfigSkipsStorePluginByDefault(t *testing.T) {
	enabled := true
	cfg := &config.Config{
		Plugins: config.PluginsConfig{
			Enabled: true,
			Configs: map[string]config.PluginInstanceConfig{
				"local-provider": {
					Enabled: &enabled,
				},
				"store-executor": pluginRuntimeConfigFromYAML(t, `
enabled: true
store:
  id: store-executor
  name: Store Executor
  description: Runs on CPA.
  author: owner
  version: 0.2.0
  release-tag: v0.2.0
  repository: https://github.com/owner/store-executor
`),
			},
		},
	}

	runtimeCfg := pluginRuntimeConfig(cfg)
	if _, ok := runtimeCfg.Configs["local-provider"]; !ok {
		t.Fatalf("local-provider missing from runtime configs")
	}
	if _, ok := runtimeCfg.Configs["store-executor"]; ok {
		t.Fatalf("store-executor present in Home runtime configs, want skipped by default")
	}
}

func TestPluginRuntimeConfigAllowsExplicitHomeLoadedStorePlugin(t *testing.T) {
	cfg := &config.Config{
		Plugins: config.PluginsConfig{
			Enabled: true,
			Configs: map[string]config.PluginInstanceConfig{
				"store-provider": pluginRuntimeConfigFromYAML(t, `
enabled: true
load-in-home: true
store:
  id: store-provider
  name: Store Provider
  description: Runs in Home.
  author: owner
  version: 0.2.0
  release-tag: v0.2.0
  repository: https://github.com/owner/store-provider
`),
			},
		},
	}

	runtimeCfg := pluginRuntimeConfig(cfg)
	if _, ok := runtimeCfg.Configs["store-provider"]; !ok {
		t.Fatalf("store-provider missing from runtime configs, want explicit Home load")
	}
}

func TestPluginRuntimeConfigUsesPluginCacheDir(t *testing.T) {
	root := filepath.Join(t.TempDir(), "plugins")
	cfg := &config.Config{
		Plugins: config.PluginsConfig{
			Enabled: true,
			Dir:     root,
		},
	}

	runtimeCfg := pluginRuntimeConfig(cfg)
	want := filepath.Clean(root)
	if runtimeCfg.Dir != want {
		t.Fatalf("runtime dir = %q, want %q", runtimeCfg.Dir, want)
	}
}

func pluginRuntimeConfigFromYAML(t *testing.T, text string) config.PluginInstanceConfig {
	t.Helper()
	var item config.PluginInstanceConfig
	if errUnmarshal := yaml.Unmarshal([]byte(text), &item); errUnmarshal != nil {
		t.Fatalf("unmarshal plugin config: %v", errUnmarshal)
	}
	return item
}
