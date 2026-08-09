package config

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"

	"gopkg.in/yaml.v3"
)

// DisableImageGenerationMode is a tri-state config value for disable-image-generation.
//
// It supports:
//   - false: enabled
//   - true: disabled everywhere (including /v1/images/* endpoints)
//   - "chat": disabled for all non-images endpoints, but enabled for /v1/images/generations and /v1/images/edits
type DisableImageGenerationMode int

const (
	DisableImageGenerationOff DisableImageGenerationMode = iota
	DisableImageGenerationAll
	DisableImageGenerationChat
)

// String returns the string representation.
func (m DisableImageGenerationMode) String() string {
	switch m {
	case DisableImageGenerationOff:
		return "false"
	case DisableImageGenerationAll:
		return "true"
	case DisableImageGenerationChat:
		return "chat"
	default:
		return "false"
	}
}

// MarshalYAML encodes a yaml.
func (m DisableImageGenerationMode) MarshalYAML() (any, error) {
	switch m {
	case DisableImageGenerationAll:
		return true, nil
	case DisableImageGenerationChat:
		return "chat", nil
	default:
		return false, nil
	}
}

// UnmarshalYAML decodes a yaml.
func (m *DisableImageGenerationMode) UnmarshalYAML(value *yaml.Node) error {
	mode, err := parseDisableImageGenerationNode(value)
	if err != nil {
		return err
	}
	*m = mode
	return nil
}

// MarshalJSON encodes a json.
func (m DisableImageGenerationMode) MarshalJSON() ([]byte, error) {
	switch m {
	case DisableImageGenerationAll:
		return []byte("true"), nil
	case DisableImageGenerationChat:
		return json.Marshal("chat")
	default:
		return []byte("false"), nil
	}
}

// UnmarshalJSON decodes a json.
func (m *DisableImageGenerationMode) UnmarshalJSON(data []byte) error {
	mode, err := parseDisableImageGenerationJSON(data)
	if err != nil {
		return err
	}
	*m = mode
	return nil
}

// parseDisableImageGenerationNode parses a disable image generation node.
func parseDisableImageGenerationNode(value *yaml.Node) (DisableImageGenerationMode, error) {
	if value == nil {
		return DisableImageGenerationOff, nil
	}

	// First try a typed bool decode (covers unquoted true/false and YAML 1.1 bools).
	var b bool
	if err := value.Decode(&b); err == nil && value.Kind == yaml.ScalarNode && value.ShortTag() == "!!bool" {
		if b {
			return DisableImageGenerationAll, nil
		}
		return DisableImageGenerationOff, nil
	}

	// Fall back to string decoding (covers quoted "true"/"false" and "chat").
	var s string
	if err := value.Decode(&s); err != nil {
		return DisableImageGenerationOff, fmt.Errorf("invalid disable-image-generation value")
	}
	return parseDisableImageGenerationString(s)
}

// parseDisableImageGenerationJSON parses a disable image generation json.
func parseDisableImageGenerationJSON(data []byte) (DisableImageGenerationMode, error) {
	trimmed := bytes.TrimSpace(data)
	if len(trimmed) == 0 || bytes.Equal(trimmed, []byte("null")) {
		return DisableImageGenerationOff, nil
	}

	// bool
	var b bool
	if err := json.Unmarshal(trimmed, &b); err == nil {
		if b {
			return DisableImageGenerationAll, nil
		}
		return DisableImageGenerationOff, nil
	}

	// string
	var s string
	if err := json.Unmarshal(trimmed, &s); err != nil {
		return DisableImageGenerationOff, fmt.Errorf("invalid disable-image-generation value")
	}
	return parseDisableImageGenerationString(s)
}

// parseDisableImageGenerationString parses a disable image generation string.
func parseDisableImageGenerationString(s string) (DisableImageGenerationMode, error) {
	s = strings.TrimSpace(strings.ToLower(s))
	switch s {
	case "", "false", "0", "off", "no":
		return DisableImageGenerationOff, nil
	case "true", "1", "on", "yes":
		return DisableImageGenerationAll, nil
	case "chat":
		return DisableImageGenerationChat, nil
	default:
		return DisableImageGenerationOff, fmt.Errorf("invalid disable-image-generation value %q (allowed: true, false, chat)", s)
	}
}
