package get

import (
	"net/http"
	"net/url"
	"strings"

	"github.com/tidwall/gjson"
)

// parseHeaders parses a headers.
func parseHeaders(jsonArg string) http.Header {
	headersObj := gjson.Get(jsonArg, "headers")
	headers := http.Header{}
	if !headersObj.Exists() || !headersObj.IsObject() {
		return headers
	}

	headersObj.ForEach(func(k, v gjson.Result) bool {
		key := strings.TrimSpace(k.String())
		if key == "" {
			return true
		}

		if v.Type == gjson.String {
			headers.Add(key, v.String())
			return true
		}

		if v.IsArray() {
			v.ForEach(func(_, entry gjson.Result) bool {
				if entry.Type == gjson.String {
					headers.Add(key, entry.String())
					return true
				}
				if entry.Type != gjson.Null {
					headers.Add(key, entry.String())
				}
				return true
			})
			return true
		}

		if v.Type != gjson.Null {
			headers.Add(key, v.String())
		}
		return true
	})
	return headers
}

// parseQuery parses a query.
func parseQuery(jsonArg string) url.Values {
	queryObj := gjson.Get(jsonArg, "query")
	query := url.Values{}
	if !queryObj.Exists() || !queryObj.IsObject() {
		return query
	}

	queryObj.ForEach(func(k, v gjson.Result) bool {
		key := strings.TrimSpace(k.String())
		if key == "" {
			return true
		}
		if v.Type == gjson.String {
			query.Add(key, v.String())
			return true
		}
		if v.IsArray() {
			v.ForEach(func(_, entry gjson.Result) bool {
				if entry.Type == gjson.String {
					query.Add(key, entry.String())
					return true
				}
				if entry.Type != gjson.Null {
					query.Add(key, entry.String())
				}
				return true
			})
			return true
		}
		if v.Type != gjson.Null {
			query.Add(key, v.String())
		}
		return true
	})
	return query
}
