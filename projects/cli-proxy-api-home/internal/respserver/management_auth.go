package respserver

import (
	"net"
	"strings"
)

// isClientHostAllowed reports whether client host allowed.
func isClientHostAllowed(clientIP string, allowHosts []string) bool {
	if len(allowHosts) == 0 {
		return true
	}
	clientIP = normalizeHostIP(clientIP)
	if clientIP == "" {
		return false
	}
	for _, host := range allowHosts {
		if clientIP == normalizeHostIP(host) {
			return true
		}
	}
	return false
}

// resolveRemoteIP resolves a remote ip.
func resolveRemoteIP(addr net.Addr) (ip string, localClient bool) {
	// Validate request inputs before mutating persisted state.
	if addr == nil {
		return "", false
	}

	var host string
	switch a := addr.(type) {
	case *net.TCPAddr:
		if a != nil && a.IP != nil {
			if ip4 := a.IP.To4(); ip4 != nil {
				host = ip4.String()
			} else {
				host = a.IP.String()
			}
		}
	default:
		host = addr.String()
		if h, _, err := net.SplitHostPort(host); err == nil {
			host = h
		}
		host = strings.TrimSpace(host)
		if raw, _, ok := strings.Cut(host, "%"); ok {
			host = raw
		}
		if parsed := net.ParseIP(host); parsed != nil {
			if ip4 := parsed.To4(); ip4 != nil {
				host = ip4.String()
			} else {
				host = parsed.String()
			}
		}
	}

	host = strings.TrimSpace(host)
	localClient = host == "127.0.0.1" || host == "::1"
	return host, localClient
}

// normalizeHostIP normalizes a host ip.
func normalizeHostIP(host string) string {
	host = strings.TrimSpace(host)
	if host == "" {
		return ""
	}
	if h, _, err := net.SplitHostPort(host); err == nil {
		host = h
	}
	if raw, _, ok := strings.Cut(host, "%"); ok {
		host = raw
	}
	if parsed := net.ParseIP(host); parsed != nil {
		if ip4 := parsed.To4(); ip4 != nil {
			return ip4.String()
		}
		return parsed.String()
	}
	return strings.TrimSpace(host)
}
