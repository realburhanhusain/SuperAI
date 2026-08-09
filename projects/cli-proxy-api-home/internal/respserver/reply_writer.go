package respserver

import (
	"fmt"
	"io"
	"strconv"

	"github.com/router-for-me/CLIProxyAPIHome/internal/respserver/dispatch"
)

type respWriter interface {
	io.Writer
	io.StringWriter
}

// writeDispatchReply writes a dispatch reply.
func writeDispatchReply(writer respWriter, reply dispatch.Reply) error {
	// Build the candidate view before applying availability rules.
	switch reply.Kind {
	case dispatch.ReplyKindSimpleString:
		return writeRedisSimpleString(writer, reply.SimpleString)
	case dispatch.ReplyKindBulkString:
		return writeRedisBulkString(writer, reply.BulkString)
	case dispatch.ReplyKindRedisError:
		return writeRedisError(writer, reply.RedisError)
	case dispatch.ReplyKindInteger:
		return writeRedisInteger(writer, reply.Integer)
	case dispatch.ReplyKindArray:
		if reply.Array == nil {
			if _, errWrite := writer.WriteString("*0\r\n"); errWrite != nil {
				return errWrite
			}
			return nil
		}
		if _, errWrite := writer.WriteString("*" + strconv.Itoa(len(reply.Array)) + "\r\n"); errWrite != nil {
			return errWrite
		}
		for _, entry := range reply.Array {
			if errWrite := writeDispatchReply(writer, entry); errWrite != nil {
				return errWrite
			}
		}
		return nil
	default:
		return writeRedisError(writer, fmt.Sprintf("ERR unsupported reply kind: %d", reply.Kind))
	}
}
