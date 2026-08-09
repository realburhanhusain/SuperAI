package errors

import "strings"

// SplitRedisErrorMessage converts "type: message" formatted strings into
// structured (type, message) pairs for RESP JSON error responses.
//
// It intentionally only treats the prefix as a type when it looks like a
// machine-readable code (lowercase snake_case).
func SplitRedisErrorMessage(message string) (string, string) {
	// Keep validation before state changes so failures leave existing data intact.
	message = strings.TrimSpace(message)
	if message == "" {
		return TypeError, MessageError
	}

	splitIndex := strings.Index(message, ": ")
	if splitIndex <= 0 {
		return TypeError, message
	}

	typePrefix := strings.TrimSpace(message[:splitIndex])
	remainder := strings.TrimSpace(message[splitIndex+2:])
	if typePrefix == "" || remainder == "" {
		return TypeError, message
	}

	if !isStructuredRedisErrorType(typePrefix) {
		return TypeError, message
	}

	return typePrefix, remainder
}

// isStructuredRedisErrorType reports whether structured redis error type.
func isStructuredRedisErrorType(value string) bool {
	hasUnderscore := false
	for i := 0; i < len(value); i++ {
		c := value[i]
		if c >= 'a' && c <= 'z' {
			continue
		}
		if c >= '0' && c <= '9' {
			continue
		}
		if c == '_' {
			hasUnderscore = true
			continue
		}
		return false
	}
	return hasUnderscore
}
