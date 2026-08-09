package config

import (
	"encoding/json"
	"fmt"
	"strings"

	"gopkg.in/yaml.v3"
)

// PluginsConfig holds dynamic plugin distribution settings for downstream CPA nodes.
type PluginsConfig struct {
	// Enabled toggles dynamic plugin loading on downstream CPA nodes.
	Enabled bool `yaml:"enabled" json:"enabled"`
	// Dir is the downstream plugin discovery directory.
	Dir string `yaml:"dir" json:"dir"`
	// StoreSources appends third-party plugin store registries to the built-in official source.
	StoreSources []string `yaml:"store-sources,omitempty" json:"store-sources,omitempty"`
	// Configs stores per-plugin instance configuration by plugin ID.
	Configs map[string]PluginInstanceConfig `yaml:"configs" json:"configs"`
}

// PluginInstanceConfig stores host-owned plugin settings and the original plugin YAML subtree.
type PluginInstanceConfig struct {
	// Enabled toggles this plugin instance. Nil is normalized to false during YAML parsing.
	Enabled *bool `yaml:"enabled,omitempty" json:"enabled,omitempty"`
	// Priority controls plugin startup and routing order.
	Priority int `yaml:"priority,omitempty" json:"priority,omitempty"`
	// Raw preserves the full original plugin configuration YAML subtree.
	Raw yaml.Node `yaml:"-" json:"-"`
}

// UnmarshalYAML extracts host-owned fields while preserving the full original YAML node.
func (c *PluginInstanceConfig) UnmarshalYAML(value *yaml.Node) error {
	if c == nil {
		return nil
	}

	c.Priority = 0
	defaultEnabled := false
	c.Enabled = &defaultEnabled

	if value == nil || value.Kind == 0 {
		c.Raw = *defaultPluginInstanceConfigNode()
		return nil
	}

	c.Raw = *deepCopyYAMLNode(value)
	if value.Kind != yaml.MappingNode {
		return nil
	}

	for i := 0; i+1 < len(value.Content); i += 2 {
		key := value.Content[i]
		node := value.Content[i+1]
		if key == nil {
			continue
		}
		switch key.Value {
		case "enabled":
			var enabled bool
			if errDecodeEnabled := node.Decode(&enabled); errDecodeEnabled != nil {
				return fmt.Errorf("parse plugin enabled: %w", errDecodeEnabled)
			}
			c.Enabled = &enabled
		case "priority":
			var priority int
			if errDecodePriority := node.Decode(&priority); errDecodePriority != nil {
				return fmt.Errorf("parse plugin priority: %w", errDecodePriority)
			}
			c.Priority = priority
		}
	}

	return nil
}

// MarshalYAML returns the preserved raw plugin YAML subtree for lossless config output.
func (c PluginInstanceConfig) MarshalYAML() (any, error) {
	if c.Raw.Kind == 0 {
		return defaultPluginInstanceConfigNode(), nil
	}
	return deepCopyYAMLNode(&c.Raw), nil
}

// MarshalJSON returns the preserved raw plugin subtree for lossless Management API output.
func (c PluginInstanceConfig) MarshalJSON() ([]byte, error) {
	if c.Raw.Kind == 0 {
		out := map[string]any{}
		if c.Enabled != nil {
			out["enabled"] = *c.Enabled
		}
		if c.Priority != 0 {
			out["priority"] = c.Priority
		}
		return json.Marshal(out)
	}
	value, errValue := yamlNodeJSONValue(&c.Raw)
	if errValue != nil {
		return nil, errValue
	}
	return json.Marshal(value)
}

// NormalizePluginsConfig applies default plugin configuration values.
func (cfg *Config) NormalizePluginsConfig() {
	if cfg == nil {
		return
	}
	cfg.Plugins.Dir = strings.TrimSpace(cfg.Plugins.Dir)
	if cfg.Plugins.Dir == "" {
		cfg.Plugins.Dir = "plugins"
	}
	if len(cfg.Plugins.StoreSources) > 0 {
		sources := make([]string, 0, len(cfg.Plugins.StoreSources))
		for _, source := range cfg.Plugins.StoreSources {
			source = strings.TrimSpace(source)
			if source == "" {
				continue
			}
			sources = append(sources, source)
		}
		cfg.Plugins.StoreSources = sources
	}
	if cfg.Plugins.Configs == nil {
		cfg.Plugins.Configs = map[string]PluginInstanceConfig{}
	}
}

func defaultPluginInstanceConfigNode() *yaml.Node {
	return &yaml.Node{
		Kind:    yaml.MappingNode,
		Tag:     "!!map",
		Content: []*yaml.Node{},
	}
}

func deepCopyYAMLNode(node *yaml.Node) *yaml.Node {
	if node == nil {
		return nil
	}
	copyNode := *node
	if len(node.Content) > 0 {
		copyNode.Content = make([]*yaml.Node, 0, len(node.Content))
		for _, child := range node.Content {
			copyNode.Content = append(copyNode.Content, deepCopyYAMLNode(child))
		}
	}
	return &copyNode
}

func yamlNodeJSONValue(node *yaml.Node) (any, error) {
	if node == nil || node.Kind == 0 {
		return map[string]any{}, nil
	}
	var value any
	if errDecode := node.Decode(&value); errDecode != nil {
		return nil, errDecode
	}
	return normalizeJSONValue(value), nil
}

func normalizeJSONValue(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		out := make(map[string]any, len(typed))
		for key, item := range typed {
			out[key] = normalizeJSONValue(item)
		}
		return out
	case map[any]any:
		out := make(map[string]any, len(typed))
		for key, item := range typed {
			out[fmt.Sprint(key)] = normalizeJSONValue(item)
		}
		return out
	case []any:
		out := make([]any, len(typed))
		for i, item := range typed {
			out[i] = normalizeJSONValue(item)
		}
		return out
	default:
		return value
	}
}
