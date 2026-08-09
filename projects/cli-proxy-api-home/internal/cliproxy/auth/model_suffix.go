package auth

import "strings"

type suffixResult struct {
	ModelName string
	HasSuffix bool
	RawSuffix string
}

// parseModelSuffix extracts a trailing "(...)" suffix from the model string.
// It intentionally does not validate or interpret suffix values.
func parseModelSuffix(model string) suffixResult {
	lastOpen := strings.LastIndex(model, "(")
	if lastOpen == -1 {
		return suffixResult{ModelName: model, HasSuffix: false}
	}
	if !strings.HasSuffix(model, ")") {
		return suffixResult{ModelName: model, HasSuffix: false}
	}
	return suffixResult{
		ModelName: model[:lastOpen],
		HasSuffix: true,
		RawSuffix: model[lastOpen+1 : len(model)-1],
	}
}
