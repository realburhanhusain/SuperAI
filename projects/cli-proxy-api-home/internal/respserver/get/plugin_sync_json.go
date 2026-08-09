package get

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"github.com/router-for-me/CLIProxyAPI/v7/sdk/pluginstore"
)

type pluginSyncJSONBuilder struct {
	data      []byte
	size      int
	countOnly bool
	err       error
}

func marshalPluginSyncResponse(response pluginstore.PluginSyncResponse) ([]byte, error) {
	manifests := make([][]byte, len(response.Items))
	for index := range response.Items {
		raw, errMarshal := json.Marshal(response.Items[index].Manifest)
		if errMarshal != nil {
			return nil, fmt.Errorf("marshal plugin sync manifest %d: %w", index, errMarshal)
		}
		manifests[index] = raw
	}
	counter := &pluginSyncJSONBuilder{countOnly: true}
	appendPluginSyncResponseJSON(counter, response, manifests)
	if counter.err != nil {
		return nil, counter.err
	}
	raw := make([]byte, 0, counter.size)
	builder := &pluginSyncJSONBuilder{data: raw}
	appendPluginSyncResponseJSON(builder, response, manifests)
	if builder.err != nil {
		clearPluginSyncJSON(builder.data)
		return nil, builder.err
	}
	if len(builder.data) != counter.size || cap(builder.data) != counter.size {
		clearPluginSyncJSON(builder.data)
		return nil, fmt.Errorf("plugin sync JSON size changed during encoding")
	}
	return builder.data, nil
}

func appendPluginSyncResponseJSON(builder *pluginSyncJSONBuilder, response pluginstore.PluginSyncResponse, manifests [][]byte) {
	builder.appendBytes([]byte(`{"schema_version":`))
	builder.appendInt(int64(response.SchemaVersion))
	builder.appendBytes([]byte(`,"expires_at":`))
	builder.appendString(response.ExpiresAt.UTC().Format(time.RFC3339Nano))
	builder.appendBytes([]byte(`,"items":[`))
	for index := range response.Items {
		if index > 0 {
			builder.appendByte(',')
		}
		builder.appendBytes([]byte(`{"manifest":`))
		builder.appendBytes(manifests[index])
		if len(response.Items[index].Auth) > 0 {
			builder.appendBytes([]byte(`,"auth":[`))
			for authIndex := range response.Items[index].Auth {
				if authIndex > 0 {
					builder.appendByte(',')
				}
				appendResolvedAuthJSON(builder, response.Items[index].Auth[authIndex])
			}
			builder.appendByte(']')
		}
		builder.appendByte('}')
	}
	builder.appendBytes([]byte(`]}`))
}

func appendResolvedAuthJSON(builder *pluginSyncJSONBuilder, auth pluginstore.ResolvedAuthConfig) {
	builder.appendByte('{')
	first := true
	appendOptionalStringJSONField(builder, &first, "match", auth.Match)
	if len(auth.ApplyTo) > 0 {
		appendJSONFieldPrefix(builder, &first, "apply_to")
		builder.appendByte('[')
		for index, value := range auth.ApplyTo {
			if index > 0 {
				builder.appendByte(',')
			}
			builder.appendString(value)
		}
		builder.appendByte(']')
	}
	appendOptionalStringJSONField(builder, &first, "type", auth.Type)
	appendOptionalSecretJSONField(builder, &first, "token", auth.Token)
	appendOptionalSecretJSONField(builder, &first, "username", auth.Username)
	appendOptionalSecretJSONField(builder, &first, "password", auth.Password)
	appendOptionalStringJSONField(builder, &first, "header_name", auth.HeaderName)
	appendOptionalSecretJSONField(builder, &first, "header_value", auth.HeaderValue)
	builder.appendByte('}')
}

func appendOptionalStringJSONField(builder *pluginSyncJSONBuilder, first *bool, name string, value string) {
	if value == "" {
		return
	}
	appendJSONFieldPrefix(builder, first, name)
	builder.appendString(value)
}

func appendOptionalSecretJSONField(builder *pluginSyncJSONBuilder, first *bool, name string, value pluginstore.Secret) {
	if len(value) == 0 {
		return
	}
	appendJSONFieldPrefix(builder, first, name)
	builder.appendSecret(value)
}

func appendJSONFieldPrefix(builder *pluginSyncJSONBuilder, first *bool, name string) {
	if !*first {
		builder.appendByte(',')
	}
	*first = false
	builder.appendString(name)
	builder.appendByte(':')
}

func (b *pluginSyncJSONBuilder) appendByte(value byte) {
	if b == nil || b.err != nil {
		return
	}
	if b.countOnly {
		b.addSize(1)
		return
	}
	b.data = append(b.data, value)
}

func (b *pluginSyncJSONBuilder) appendBytes(value []byte) {
	if b == nil || b.err != nil {
		return
	}
	if b.countOnly {
		b.addSize(len(value))
		return
	}
	b.data = append(b.data, value...)
}

func (b *pluginSyncJSONBuilder) appendInt(value int64) {
	if b == nil || b.err != nil {
		return
	}
	if b.countOnly {
		b.addSize(len(strconv.FormatInt(value, 10)))
		return
	}
	b.data = strconv.AppendInt(b.data, value, 10)
}

func (b *pluginSyncJSONBuilder) appendString(value string) {
	if b == nil || b.err != nil {
		return
	}
	quoted, errMarshal := json.Marshal(value)
	if errMarshal != nil {
		b.err = errMarshal
		return
	}
	b.appendBytes(quoted)
}

func (b *pluginSyncJSONBuilder) appendSecret(value pluginstore.Secret) {
	if b == nil || b.err != nil {
		return
	}
	encodedLength := base64.StdEncoding.EncodedLen(len(value))
	if b.countOnly {
		b.addSize(encodedLength + 2)
		return
	}
	b.data = append(b.data, '"')
	b.data = base64.StdEncoding.AppendEncode(b.data, value)
	b.data = append(b.data, '"')
}

func (b *pluginSyncJSONBuilder) addSize(delta int) {
	if b == nil || b.err != nil || delta < 0 {
		return
	}
	maxInt := int(^uint(0) >> 1)
	if delta > maxInt-b.size {
		b.err = fmt.Errorf("plugin sync JSON exceeds supported size")
		return
	}
	b.size += delta
}

func clearPluginSyncJSON(value []byte) {
	for index := range value {
		value[index] = 0
	}
}
