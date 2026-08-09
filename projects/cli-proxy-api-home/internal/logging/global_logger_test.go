package logging

import (
	"strings"
	"testing"
	"time"

	log "github.com/sirupsen/logrus"
)

func TestLogFormatterAddsCLIProxyAPIHomePrefix(t *testing.T) {
	entry := log.NewEntry(log.StandardLogger())
	entry.Time = time.Date(2026, 5, 29, 8, 0, 0, 0, time.Local)
	entry.Level = log.InfoLevel
	entry.Message = "home runtime ready"

	raw, errFormat := (&LogFormatter{}).Format(entry)
	if errFormat != nil {
		t.Fatalf("Format error: %v", errFormat)
	}
	got := string(raw)
	wantPrefix := FormatLogSourcePrefix("CLIProxyAPIHome") + " [2026-05-29 08:00:00] [--------] [info ] "
	if !strings.HasPrefix(got, wantPrefix) {
		t.Fatalf("formatted log = %q, want CLIProxyAPIHome prefix", got)
	}
}

func TestLogFormatterPrintsPluginFields(t *testing.T) {
	entry := log.NewEntry(log.StandardLogger())
	entry.Time = time.Date(2026, 6, 25, 21, 21, 2, 0, time.Local)
	entry.Level = log.InfoLevel
	entry.Message = "pluginhost: plugin registered"
	entry.Data["plugin_id"] = "sample-provider"
	entry.Data["plugin_name"] = "Sample Provider"
	entry.Data["version"] = "0.2.0"
	entry.Data["active_version"] = "0.1.0"
	entry.Data["retired_version"] = "0.2.0"
	entry.Data["path"] = "plugins/windows/amd64/sample-provider-v0.2.0.dll"
	entry.Data["active_path"] = "plugins/windows/amd64/sample-provider-v0.1.0.dll"
	entry.Data["retired_path"] = "plugins/windows/amd64/sample-provider-v0.2.0.dll"

	raw, errFormat := (&LogFormatter{}).Format(entry)
	if errFormat != nil {
		t.Fatalf("Format error: %v", errFormat)
	}

	got := string(raw)
	for _, want := range []string{
		"plugin_id=sample-provider",
		"plugin_name=Sample Provider",
		"version=0.2.0",
		"active_version=0.1.0",
		"retired_version=0.2.0",
		"path=plugins/windows/amd64/sample-provider-v0.2.0.dll",
		"active_path=plugins/windows/amd64/sample-provider-v0.1.0.dll",
		"retired_path=plugins/windows/amd64/sample-provider-v0.2.0.dll",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("formatted log = %q, missing %s", got, want)
		}
	}
}

func TestLogFormatterOmitsGenericPathField(t *testing.T) {
	entry := log.NewEntry(log.StandardLogger())
	entry.Time = time.Date(2026, 6, 25, 21, 25, 0, 0, time.Local)
	entry.Level = log.WarnLevel
	entry.Message = "failed to load local file"
	entry.Data["path"] = "auths/private-token.json"
	entry.Data["active_path"] = "plugins/windows/amd64/sample-provider-v0.1.0.dll"
	entry.Data["retired_path"] = "plugins/windows/amd64/sample-provider-v0.2.0.dll"

	raw, errFormat := (&LogFormatter{}).Format(entry)
	if errFormat != nil {
		t.Fatalf("Format error: %v", errFormat)
	}

	got := string(raw)
	for _, forbidden := range []string{"path=", "active_path=", "retired_path="} {
		if strings.Contains(got, forbidden) {
			t.Fatalf("formatted log = %q, want generic %s omitted", got, forbidden)
		}
	}
}

func TestFormatLogSourcePrefixAlignsHomeIPv4AndIPv6(t *testing.T) {
	home := FormatLogSourcePrefix("CLIProxyAPIHome")
	ipv4 := FormatLogSourcePrefix("255.255.255.255")
	ipv6 := FormatLogSourcePrefix("2001:db8:85a3::8a2e:370:7334")

	if len(home) != len(ipv4) {
		t.Fatalf("home prefix len = %d, ipv4 prefix len = %d", len(home), len(ipv4))
	}
	if len(home) != len(ipv6) {
		t.Fatalf("home prefix len = %d, ipv6 prefix len = %d", len(home), len(ipv6))
	}
	if home != "[CLIProxyAPIHome]" {
		t.Fatalf("home prefix = %q, want bracketed CLIProxyAPIHome source", home)
	}
	if ipv6 != "[::8a2e:370:7334]" {
		t.Fatalf("ipv6 prefix = %q, want rightmost IPv4-width address", ipv6)
	}
}
