package protocolmux

import (
	"bufio"
	"context"
	"crypto/tls"
	"errors"
	"net"
	"net/http"
	"strings"

	log "github.com/sirupsen/logrus"
)

// IsRESPPrefix reports whether is resp prefix.
func IsRESPPrefix(prefix byte) bool {
	switch prefix {
	case '*', '$', '+', '-', ':':
		return true
	default:
		return false
	}
}

// Serve handles serve.
func Serve(ctx context.Context, listener net.Listener, httpListener *Listener, onRESPConn func(net.Conn), onHTTPConn func(net.Conn), tlsConfig *tls.Config) error {
	// Decode the wire frame before dispatching command handling.
	if listener == nil {
		return net.ErrClosed
	}
	if ctx == nil {
		ctx = context.Background()
	}

	for {
		conn, errAccept := listener.Accept()
		if errAccept != nil {
			return errAccept
		}
		if conn == nil {
			continue
		}

		if routed := routeTLSConn(conn, httpListener, onHTTPConn); routed {
			continue
		}

		reader := bufio.NewReader(conn)
		prefix, errPeek := reader.Peek(1)
		if errPeek != nil {
			if errClose := conn.Close(); errClose != nil {
				log.Errorf("protocol mux: close conn after peek error: %v", errClose)
			}
			continue
		}

		if tlsConfig != nil && isTLSClientHello(prefix[0]) {
			tlsConn := tls.Server(&BufferedConn{Conn: conn, reader: reader}, tlsConfig)
			if errHandshake := tlsConn.Handshake(); errHandshake != nil {
				if errClose := conn.Close(); errClose != nil {
					log.Errorf("protocol mux: close conn after TLS handshake error: %v", errClose)
				}
				continue
			}
			if routed := routeTLSConn(tlsConn, httpListener, onHTTPConn); routed {
				continue
			}
			reader = bufio.NewReader(tlsConn)
			prefix, errPeek = reader.Peek(1)
			if errPeek != nil {
				if errClose := tlsConn.Close(); errClose != nil {
					log.Errorf("protocol mux: close tls conn after peek error: %v", errClose)
				}
				continue
			}
			conn = tlsConn
		}

		wrapped := &BufferedConn{Conn: conn, reader: reader}
		if IsRESPPrefix(prefix[0]) {
			if onRESPConn != nil {
				onRESPConn(wrapped)
			} else {
				_ = wrapped.Close()
			}
			continue
		}

		if onHTTPConn != nil {
			onHTTPConn(wrapped)
			continue
		}
		if httpListener == nil {
			_ = wrapped.Close()
			continue
		}
		if errPut := httpListener.Put(wrapped); errPut != nil {
			if errClose := wrapped.Close(); errClose != nil {
				log.Errorf("protocol mux: close conn after http route failure: %v", errClose)
			}
		}
	}
}

func routeTLSConn(conn net.Conn, httpListener *Listener, onHTTPConn func(net.Conn)) bool {
	tlsConn, ok := conn.(*tls.Conn)
	if !ok {
		return false
	}
	if errHandshake := tlsConn.Handshake(); errHandshake != nil {
		if errClose := conn.Close(); errClose != nil {
			log.Errorf("protocol mux: close conn after TLS handshake error: %v", errClose)
		}
		return true
	}
	proto := strings.TrimSpace(tlsConn.ConnectionState().NegotiatedProtocol)
	if proto != "h2" && proto != "http/1.1" {
		return false
	}
	if onHTTPConn != nil {
		onHTTPConn(tlsConn)
	} else if httpListener != nil {
		_ = httpListener.Put(tlsConn)
	} else {
		_ = conn.Close()
	}
	return true
}

func isTLSClientHello(prefix byte) bool {
	return prefix == 0x16
}

// NormalizeServeError normalizes a serve error.
func NormalizeServeError(err error) error {
	if err == nil {
		return nil
	}
	if errors.Is(err, net.ErrClosed) {
		return nil
	}
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}
