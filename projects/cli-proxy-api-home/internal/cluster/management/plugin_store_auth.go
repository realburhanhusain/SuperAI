package management

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPI/v7/sdk/pluginstore"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"github.com/router-for-me/CLIProxyAPIHome/internal/pluginauth"
	"gorm.io/gorm"
)

const pluginStoreAuthMaxRequestBodySize int64 = 64 << 10

type pluginStoreAuthRequestSecret struct {
	value pluginstore.Secret
}

func (s *pluginStoreAuthRequestSecret) UnmarshalText(text []byte) error {
	defer clearPluginStoreAuthBytes(text)
	if s == nil {
		return fmt.Errorf("plugin store auth secret target is nil")
	}
	s.Clear()
	s.value = append(pluginstore.Secret(nil), text...)
	return nil
}

func (s *pluginStoreAuthRequestSecret) Clear() {
	if s != nil {
		s.value.Clear()
	}
}

func (s *pluginStoreAuthRequestSecret) Value() pluginstore.Secret {
	if s == nil {
		return nil
	}
	return s.value
}

func (s *pluginStoreAuthRequestSecret) Pointer() *pluginstore.Secret {
	if s == nil {
		return nil
	}
	return &s.value
}

type optionalPluginStoreAuthRequestSecret struct {
	secret  pluginStoreAuthRequestSecret
	present bool
}

func (s *optionalPluginStoreAuthRequestSecret) UnmarshalJSON(raw []byte) error {
	if s == nil {
		return fmt.Errorf("optional plugin store auth secret target is nil")
	}
	s.Clear()
	if bytes.Equal(raw, []byte("null")) {
		return nil
	}
	if errDecode := json.Unmarshal(raw, &s.secret); errDecode != nil {
		return errDecode
	}
	s.present = true
	return nil
}

func (s *optionalPluginStoreAuthRequestSecret) Clear() {
	if s == nil {
		return
	}
	s.secret.Clear()
	s.present = false
}

func (s *optionalPluginStoreAuthRequestSecret) Value() pluginstore.Secret {
	if s == nil || !s.present {
		return nil
	}
	return s.secret.Value()
}

func (s *optionalPluginStoreAuthRequestSecret) Pointer() *pluginstore.Secret {
	if s == nil || !s.present {
		return nil
	}
	return s.secret.Pointer()
}

type createPluginStoreAuthRequest struct {
	Name        string                       `json:"name"`
	Match       string                       `json:"match"`
	ApplyTo     []string                     `json:"apply_to"`
	AuthType    string                       `json:"auth_type"`
	Token       pluginStoreAuthRequestSecret `json:"token"`
	Username    pluginStoreAuthRequestSecret `json:"username"`
	Password    pluginStoreAuthRequestSecret `json:"password"`
	HeaderName  string                       `json:"header_name"`
	HeaderValue pluginStoreAuthRequestSecret `json:"header_value"`
	Enabled     *bool                        `json:"enabled"`
}

func (r *createPluginStoreAuthRequest) Clear() {
	if r == nil {
		return
	}
	r.Token.Clear()
	r.Username.Clear()
	r.Password.Clear()
	r.HeaderValue.Clear()
}

type updatePluginStoreAuthRequest struct {
	Name        *string                              `json:"name"`
	Match       *string                              `json:"match"`
	ApplyTo     *[]string                            `json:"apply_to"`
	AuthType    *string                              `json:"auth_type"`
	Token       optionalPluginStoreAuthRequestSecret `json:"token"`
	Username    optionalPluginStoreAuthRequestSecret `json:"username"`
	Password    optionalPluginStoreAuthRequestSecret `json:"password"`
	HeaderName  *string                              `json:"header_name"`
	HeaderValue optionalPluginStoreAuthRequestSecret `json:"header_value"`
	Enabled     *bool                                `json:"enabled"`
}

func (r *updatePluginStoreAuthRequest) Clear() {
	if r == nil {
		return
	}
	r.Token.Clear()
	r.Username.Clear()
	r.Password.Clear()
	r.HeaderValue.Clear()
}

func (h *Handler) ListPluginStoreAuth(c *gin.Context) {
	ctx, cancel := h.requestContext(c)
	defer cancel()
	items, errList := h.pluginStoreAuth.List(ctx)
	if errList != nil {
		respondError(c, http.StatusInternalServerError, "plugin_store_auth_list_failed", errList)
		return
	}
	c.JSON(http.StatusOK, gin.H{"items": items})
}

func (h *Handler) CreatePluginStoreAuth(c *gin.Context) {
	var request createPluginStoreAuthRequest
	defer request.Clear()
	if errBind := decodePluginStoreAuthRequest(c, &request); errBind != nil {
		respondPluginStoreAuthRequestError(c, errBind)
		return
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()
	entry, errCreate := h.pluginStoreAuth.Create(ctx, pluginauth.CreateInput{
		Name: request.Name, Match: request.Match, ApplyTo: request.ApplyTo, AuthType: request.AuthType,
		Token: request.Token.Value(), Username: request.Username.Value(), Password: request.Password.Value(),
		HeaderName: request.HeaderName, HeaderValue: request.HeaderValue.Value(), Enabled: request.Enabled,
	})
	if errCreate != nil {
		respondPluginStoreAuthError(c, "plugin_store_auth_create_failed", errCreate)
		return
	}
	c.JSON(http.StatusCreated, entry)
}

func (h *Handler) GetPluginStoreAuth(c *gin.Context) {
	id, okID := pluginStoreAuthID(c)
	if !okID {
		return
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()
	entry, errGet := h.pluginStoreAuth.Get(ctx, id)
	if errGet != nil {
		respondPluginStoreAuthError(c, "plugin_store_auth_get_failed", errGet)
		return
	}
	c.JSON(http.StatusOK, entry)
}

func (h *Handler) UpdatePluginStoreAuth(c *gin.Context) {
	id, okID := pluginStoreAuthID(c)
	if !okID {
		return
	}
	var request updatePluginStoreAuthRequest
	defer request.Clear()
	if errBind := decodePluginStoreAuthRequest(c, &request); errBind != nil {
		respondPluginStoreAuthRequestError(c, errBind)
		return
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()
	entry, errUpdate := h.pluginStoreAuth.Update(ctx, id, pluginauth.UpdateInput{
		Name: request.Name, Match: request.Match, ApplyTo: request.ApplyTo, AuthType: request.AuthType,
		Token: request.Token.Pointer(), Username: request.Username.Pointer(), Password: request.Password.Pointer(),
		HeaderName: request.HeaderName, HeaderValue: request.HeaderValue.Pointer(), Enabled: request.Enabled,
	})
	if errUpdate != nil {
		respondPluginStoreAuthError(c, "plugin_store_auth_update_failed", errUpdate)
		return
	}
	c.JSON(http.StatusOK, entry)
}

func (h *Handler) DeletePluginStoreAuth(c *gin.Context) {
	id, okID := pluginStoreAuthID(c)
	if !okID {
		return
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()
	if errDelete := h.pluginStoreAuth.Delete(ctx, id); errDelete != nil {
		respondPluginStoreAuthError(c, "plugin_store_auth_delete_failed", errDelete)
		return
	}
	respondOK(c)
}

func pluginStoreAuthID(c *gin.Context) (uint, bool) {
	value := strings.TrimSpace(c.Param("id"))
	parsed, errParse := strconv.ParseUint(value, 10, strconv.IntSize-1)
	if errParse != nil || parsed == 0 {
		respondError(c, http.StatusBadRequest, "invalid_plugin_store_auth_id", fmt.Errorf("plugin store auth id is invalid"))
		return 0, false
	}
	return uint(parsed), true
}

func respondPluginStoreAuthError(c *gin.Context, code string, err error) {
	status := http.StatusInternalServerError
	if errors.Is(err, pluginauth.ErrInvalidInput) {
		status = http.StatusUnprocessableEntity
		code = "plugin_store_auth_invalid"
	} else if errors.Is(err, gorm.ErrRecordNotFound) {
		status = http.StatusNotFound
	} else if errors.Is(err, cluster.ErrPluginStoreAuthConflict) {
		status = http.StatusConflict
	}
	respondError(c, status, code, err)
}

func respondPluginStoreAuthRequestError(c *gin.Context, err error) {
	status := http.StatusBadRequest
	var maxBytesError *http.MaxBytesError
	if errors.As(err, &maxBytesError) {
		status = http.StatusRequestEntityTooLarge
	}
	respondError(c, status, "invalid_request", err)
}

func decodePluginStoreAuthRequest(c *gin.Context, target any) error {
	if c == nil || c.Request == nil || c.Request.Body == nil {
		return fmt.Errorf("plugin store auth request body is unavailable")
	}
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, pluginStoreAuthMaxRequestBodySize)
	raw, errRead := io.ReadAll(c.Request.Body)
	if errRead != nil {
		clearPluginStoreAuthBytes(raw)
		return errRead
	}
	return decodePluginStoreAuthJSON(raw, target)
}

func decodePluginStoreAuthJSON(raw []byte, target any) error {
	defer clearPluginStoreAuthBytes(raw)
	trimmed := bytes.TrimSpace(raw)
	if len(trimmed) == 0 || trimmed[0] != '{' {
		return fmt.Errorf("plugin store auth request must be a JSON object")
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if errDecode := decoder.Decode(target); errDecode != nil {
		return errDecode
	}
	offset := decoder.InputOffset()
	if offset < 0 || offset > int64(len(raw)) || len(bytes.TrimSpace(raw[offset:])) != 0 {
		return fmt.Errorf("plugin store auth request must contain one JSON value")
	}
	return nil
}

func clearPluginStoreAuthBytes(value []byte) {
	for index := range value {
		value[index] = 0
	}
}
