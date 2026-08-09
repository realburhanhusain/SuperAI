package logging

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

var (
	setupOnce sync.Once
)

const logSourceLabelWidth = len("255.255.255.255")

// LogFormatter defines a custom log format for logrus.
// This formatter adds source, timestamp, level, request ID, and source location to each log entry.
// Format: [CLIProxyAPIHome] [2025-12-23 20:14:04] [debug] [manager.go:524] | a1b2c3d4 | Use API key sk-9...0RHO for model gpt-5.2
type LogFormatter struct{}

// FormatLogSourcePrefix renders a fixed-width log source column.
func FormatLogSourcePrefix(source string) string {
	source = strings.TrimSpace(source)
	if source == "" {
		source = "UNKNOWN"
	}
	sourceRunes := []rune(source)
	if len(sourceRunes) > logSourceLabelWidth {
		source = string(sourceRunes[len(sourceRunes)-logSourceLabelWidth:])
	}
	return fmt.Sprintf("[%-*s]", logSourceLabelWidth, source)
}

// logFieldOrder defines the display order for common log fields.
var logFieldOrder = []string{
	"provider", "model",
	"plugin_id", "plugin_name", "source_id",
	"version", "active_version", "retired_version", "overwritten",
	"mode", "budget", "level", "original_mode", "original_value", "min", "max", "clamped_to", "error",
}

var pluginPathFieldOrder = []string{"path", "active_path", "retired_path"}

// Format renders a single log entry with custom formatting.
func (m *LogFormatter) Format(entry *log.Entry) ([]byte, error) {
	var buffer *bytes.Buffer
	if entry.Buffer != nil {
		buffer = entry.Buffer
	} else {
		buffer = &bytes.Buffer{}
	}

	timestamp := entry.Time.Format("2006-01-02 15:04:05")
	message := strings.TrimRight(entry.Message, "\r\n")

	reqID := "--------"
	if id, ok := entry.Data["request_id"].(string); ok && id != "" {
		reqID = id
	}

	level := entry.Level.String()
	if level == "warning" {
		level = "warn"
	}
	levelStr := fmt.Sprintf("%-5s", level)

	// Build fields string (only print fields in logFieldOrder)
	var fieldsStr string
	if len(entry.Data) > 0 {
		var fields []string
		for _, k := range logFieldOrder {
			if v, ok := entry.Data[k]; ok {
				fields = append(fields, fmt.Sprintf("%s=%v", k, v))
			}
		}
		if pluginID, ok := entry.Data["plugin_id"]; ok && strings.TrimSpace(fmt.Sprint(pluginID)) != "" {
			for _, k := range pluginPathFieldOrder {
				if v, ok := entry.Data[k]; ok {
					fields = append(fields, fmt.Sprintf("%s=%v", k, v))
				}
			}
		}
		if len(fields) > 0 {
			fieldsStr = " " + strings.Join(fields, " ")
		}
	}

	sourcePrefix := FormatLogSourcePrefix("CLIProxyAPIHome")
	var formatted string
	if entry.Caller != nil {
		formatted = fmt.Sprintf("%s [%s] [%s] [%s] [%s:%d] %s%s\n", sourcePrefix, timestamp, reqID, levelStr, filepath.Base(entry.Caller.File), entry.Caller.Line, message, fieldsStr)
	} else {
		formatted = fmt.Sprintf("%s [%s] [%s] [%s] %s%s\n", sourcePrefix, timestamp, reqID, levelStr, message, fieldsStr)
	}
	buffer.WriteString(formatted)

	return buffer.Bytes(), nil
}

// SetupBaseLogger configures the shared logrus instance.
// It is safe to call multiple times; initialization happens only once.
func SetupBaseLogger() {
	setupOnce.Do(func() {
		log.SetOutput(os.Stdout)
		log.SetReportCaller(true)
		log.SetFormatter(&LogFormatter{})

		// Redirect Gin debug prints (route registration, warnings) into logrus,
		// so startup logs share the same format as the rest of the application.
		gin.DefaultWriter = log.StandardLogger().Writer()
		gin.DefaultErrorWriter = log.StandardLogger().WriterLevel(log.ErrorLevel)
		gin.DebugPrintRouteFunc = func(httpMethod, absolutePath, handlerName string, nuHandlers int) {
			log.StandardLogger().Infof("%-6s %-25s --> %s (%d handlers)", httpMethod, absolutePath, handlerName, nuHandlers)
		}
		gin.DebugPrintFunc = func(format string, values ...interface{}) {
			format = strings.TrimRight(format, "\r\n")
			log.StandardLogger().Infof(format, values...)
		}
	})
}
