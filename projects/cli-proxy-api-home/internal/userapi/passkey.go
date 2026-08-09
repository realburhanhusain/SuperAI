package userapi

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-webauthn/webauthn/protocol"
	"github.com/go-webauthn/webauthn/webauthn"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
)

const (
	webAuthnSessionProvider     = "webauthn"
	webAuthnCeremonyRegister    = "passkey_register"
	webAuthnCeremonyLogin       = "passkey_login"
	webAuthnSessionErrorMessage = "WebAuthn ceremony failed"
)

type passkeyEntry struct {
	ID         string               `json:"id"`
	Name       string               `json:"name,omitempty"`
	Credential *webauthn.Credential `json:"credential,omitempty"`
	CreatedAt  time.Time            `json:"created_at,omitempty"`
	UpdatedAt  time.Time            `json:"updated_at,omitempty"`
}

type passkeyUser struct {
	id          []byte
	name        string
	displayName string
	credentials []webauthn.Credential
}

type webAuthnSessionPayload struct {
	Ceremony string               `json:"ceremony"`
	UserID   uint                 `json:"user_id"`
	Session  webauthn.SessionData `json:"session"`
}

func loadPasskeys(raw cluster.JSONB) ([]passkeyEntry, error) {
	if len(raw) == 0 || strings.EqualFold(strings.TrimSpace(string(raw)), "null") {
		return nil, nil
	}
	var entries []passkeyEntry
	if errArray := json.Unmarshal(raw, &entries); errArray == nil {
		return normalizePasskeys(entries), nil
	}
	var wrapped struct {
		Passkeys []passkeyEntry `json:"passkeys"`
	}
	if errWrapped := json.Unmarshal(raw, &wrapped); errWrapped == nil && len(wrapped.Passkeys) > 0 {
		return normalizePasskeys(wrapped.Passkeys), nil
	}
	var single passkeyEntry
	if errSingle := json.Unmarshal(raw, &single); errSingle == nil && strings.TrimSpace(single.ID) != "" {
		return normalizePasskeys([]passkeyEntry{single}), nil
	}
	return nil, fmt.Errorf("invalid passkey data")
}

func passkeyEnabled(raw cluster.JSONB) (bool, error) {
	entries, errLoad := loadPasskeys(raw)
	if errLoad != nil {
		return false, errLoad
	}
	return len(passkeyCredentials(entries)) > 0, nil
}

func marshalPasskeys(entries []passkeyEntry) (cluster.JSONB, error) {
	entries = normalizePasskeys(entries)
	raw, errMarshal := json.Marshal(entries)
	if errMarshal != nil {
		return nil, errMarshal
	}
	return cluster.JSONB(raw), nil
}

func normalizePasskeys(entries []passkeyEntry) []passkeyEntry {
	if len(entries) == 0 {
		return nil
	}
	out := make([]passkeyEntry, 0, len(entries))
	seen := make(map[string]struct{}, len(entries))
	for _, entry := range entries {
		entry.ID = strings.TrimSpace(entry.ID)
		if entry.ID == "" {
			continue
		}
		if _, ok := seen[entry.ID]; ok {
			continue
		}
		seen[entry.ID] = struct{}{}
		entry.Name = strings.TrimSpace(entry.Name)
		if entry.Credential != nil && !validWebAuthnCredential(entry.Credential) {
			entry.Credential = nil
		}
		out = append(out, entry)
	}
	return out
}

func passkeyPublic(entry passkeyEntry) map[string]any {
	out := map[string]any{
		"id":         entry.ID,
		"name":       entry.Name,
		"created_at": entry.CreatedAt,
		"updated_at": entry.UpdatedAt,
	}
	return out
}

func newPasskeyUser(record *cluster.UserRecord) (*passkeyUser, []passkeyEntry, error) {
	if record == nil {
		return nil, nil, fmt.Errorf("user record is nil")
	}
	entries, errEntries := loadPasskeys(record.Passkey)
	if errEntries != nil {
		return nil, nil, errEntries
	}
	user := &passkeyUser{
		id:          webAuthnUserID(record.ID),
		name:        strings.TrimSpace(record.Username),
		displayName: strings.TrimSpace(record.Username),
		credentials: passkeyCredentials(entries),
	}
	return user, entries, nil
}

func (u *passkeyUser) WebAuthnID() []byte {
	if u == nil {
		return nil
	}
	return append([]byte(nil), u.id...)
}

func (u *passkeyUser) WebAuthnName() string {
	if u == nil {
		return ""
	}
	return u.name
}

func (u *passkeyUser) WebAuthnDisplayName() string {
	if u == nil {
		return ""
	}
	return u.displayName
}

func (u *passkeyUser) WebAuthnCredentials() []webauthn.Credential {
	if u == nil {
		return nil
	}
	return append([]webauthn.Credential(nil), u.credentials...)
}

func passkeyCredentials(entries []passkeyEntry) []webauthn.Credential {
	if len(entries) == 0 {
		return nil
	}
	credentials := make([]webauthn.Credential, 0, len(entries))
	for _, entry := range entries {
		if !validWebAuthnCredential(entry.Credential) {
			continue
		}
		credentials = append(credentials, *entry.Credential)
	}
	return credentials
}

func validWebAuthnCredential(credential *webauthn.Credential) bool {
	return credential != nil && len(credential.ID) > 0 && len(credential.PublicKey) > 0
}

func addPasskeyCredential(raw cluster.JSONB, name string, credential *webauthn.Credential) (cluster.JSONB, passkeyEntry, error) {
	if !validWebAuthnCredential(credential) {
		return nil, passkeyEntry{}, fmt.Errorf("webauthn credential is required")
	}
	entries, errEntries := loadPasskeys(raw)
	if errEntries != nil {
		return nil, passkeyEntry{}, errEntries
	}
	id := webAuthnCredentialID(credential.ID)
	if id == "" {
		return nil, passkeyEntry{}, fmt.Errorf("webauthn credential id is required")
	}
	for _, entry := range entries {
		if entry.ID == id {
			return nil, passkeyEntry{}, fmt.Errorf("passkey already exists")
		}
	}
	now := time.Now().UTC()
	entry := passkeyEntry{
		ID:         id,
		Name:       strings.TrimSpace(name),
		Credential: credential,
		CreatedAt:  now,
		UpdatedAt:  now,
	}
	entries = append(entries, entry)
	rawNext, errMarshal := marshalPasskeys(entries)
	if errMarshal != nil {
		return nil, passkeyEntry{}, errMarshal
	}
	return rawNext, entry, nil
}

func updatePasskeyCredential(raw cluster.JSONB, credential *webauthn.Credential) (cluster.JSONB, error) {
	if !validWebAuthnCredential(credential) {
		return nil, fmt.Errorf("webauthn credential is required")
	}
	entries, errEntries := loadPasskeys(raw)
	if errEntries != nil {
		return nil, errEntries
	}
	id := webAuthnCredentialID(credential.ID)
	for i := range entries {
		if entries[i].ID != id {
			continue
		}
		entries[i].Credential = credential
		entries[i].UpdatedAt = time.Now().UTC()
		return marshalPasskeys(entries)
	}
	return nil, fmt.Errorf("passkey not found")
}

func webAuthnCredentialID(id []byte) string {
	if len(id) == 0 {
		return ""
	}
	return base64.RawURLEncoding.EncodeToString(id)
}

func webAuthnUserID(id uint) []byte {
	return []byte("cpah-user-" + strconv.FormatUint(uint64(id), 10))
}

func (h *Handler) beginPasskeyRegistration(c *gin.Context, ctx context.Context, record *cluster.UserRecord) (*protocol.CredentialCreation, string, error) {
	user, entries, errUser := newPasskeyUser(record)
	if errUser != nil {
		return nil, "", errUser
	}
	rp, errRP := webAuthnForRequest(c)
	if errRP != nil {
		return nil, "", errRP
	}
	credentials := passkeyCredentials(entries)
	options := []webauthn.RegistrationOption{
		webauthn.WithAuthenticatorSelection(protocol.AuthenticatorSelection{
			ResidentKey:      protocol.ResidentKeyRequirementPreferred,
			UserVerification: protocol.VerificationRequired,
		}),
		webauthn.WithExclusions(webauthn.Credentials(credentials).CredentialDescriptors()),
		webauthn.WithExtensions(map[string]any{"credProps": true}),
	}
	creation, session, errBegin := rp.BeginRegistration(user, options...)
	if errBegin != nil {
		return nil, "", errBegin
	}
	challengeID, errStore := h.storeWebAuthnSession(ctx, webAuthnCeremonyRegister, record.ID, session)
	if errStore != nil {
		return nil, "", errStore
	}
	return creation, challengeID, nil
}

func (h *Handler) finishPasskeyRegistration(c *gin.Context, ctx context.Context, record *cluster.UserRecord, challengeID string, credentialRaw json.RawMessage, name string) (passkeyEntry, error) {
	user, _, errUser := newPasskeyUser(record)
	if errUser != nil {
		return passkeyEntry{}, errUser
	}
	session, errSession := h.loadWebAuthnSession(ctx, challengeID, webAuthnCeremonyRegister, record.ID)
	if errSession != nil {
		return passkeyEntry{}, errSession
	}
	rp, errRP := webAuthnForRequest(c)
	if errRP != nil {
		return passkeyEntry{}, errRP
	}
	parsed, errParse := protocol.ParseCredentialCreationResponseBytes(credentialRaw)
	if errParse != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return passkeyEntry{}, errParse
	}
	credential, errCreate := rp.CreateCredential(user, *session, parsed)
	if errCreate != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return passkeyEntry{}, errCreate
	}
	rawNext, entry, errAdd := addPasskeyCredential(record.Passkey, name, credential)
	if errAdd != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return passkeyEntry{}, errAdd
	}
	if _, errUpdate := h.repo.UpdateUser(ctx, record.ID, cluster.UserUpdate{Passkey: &rawNext}); errUpdate != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return passkeyEntry{}, errUpdate
	}
	if errComplete := h.repo.CompleteOAuthSession(ctx, challengeID); errComplete != nil {
		return passkeyEntry{}, errComplete
	}
	return entry, nil
}

func (h *Handler) beginPasskeyLogin(c *gin.Context, ctx context.Context, record *cluster.UserRecord) (*protocol.CredentialAssertion, string, error) {
	user, _, errUser := newPasskeyUser(record)
	if errUser != nil {
		return nil, "", errUser
	}
	if len(user.credentials) == 0 {
		return nil, "", fmt.Errorf("passkey is not enabled")
	}
	rp, errRP := webAuthnForRequest(c)
	if errRP != nil {
		return nil, "", errRP
	}
	assertion, session, errBegin := rp.BeginLogin(user, webauthn.WithUserVerification(protocol.VerificationRequired))
	if errBegin != nil {
		return nil, "", errBegin
	}
	challengeID, errStore := h.storeWebAuthnSession(ctx, webAuthnCeremonyLogin, record.ID, session)
	if errStore != nil {
		return nil, "", errStore
	}
	return assertion, challengeID, nil
}

func (h *Handler) finishPasskeyLogin(c *gin.Context, ctx context.Context, record *cluster.UserRecord, challengeID string, credentialRaw json.RawMessage) error {
	user, _, errUser := newPasskeyUser(record)
	if errUser != nil {
		return errUser
	}
	if len(user.credentials) == 0 {
		return fmt.Errorf("passkey is not enabled")
	}
	session, errSession := h.loadWebAuthnSession(ctx, challengeID, webAuthnCeremonyLogin, record.ID)
	if errSession != nil {
		return errSession
	}
	rp, errRP := webAuthnForRequest(c)
	if errRP != nil {
		return errRP
	}
	parsed, errParse := protocol.ParseCredentialRequestResponseBytes(credentialRaw)
	if errParse != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return errParse
	}
	credential, errValidate := rp.ValidateLogin(user, *session, parsed)
	if errValidate != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return errValidate
	}
	rawNext, errUpdateCredential := updatePasskeyCredential(record.Passkey, credential)
	if errUpdateCredential != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return errUpdateCredential
	}
	if _, errUpdate := h.repo.UpdateUser(ctx, record.ID, cluster.UserUpdate{Passkey: &rawNext}); errUpdate != nil {
		_ = h.repo.SetOAuthSessionError(ctx, challengeID, webAuthnSessionErrorMessage)
		return errUpdate
	}
	if errComplete := h.repo.CompleteOAuthSession(ctx, challengeID); errComplete != nil {
		return errComplete
	}
	record.Passkey = rawNext
	return nil
}

func (h *Handler) storeWebAuthnSession(ctx context.Context, ceremony string, userID uint, session *webauthn.SessionData) (string, error) {
	if h == nil || h.repo == nil {
		return "", fmt.Errorf("user api repository is required")
	}
	if session == nil {
		return "", fmt.Errorf("webauthn session is required")
	}
	state, errState := randomToken(24)
	if errState != nil {
		return "", errState
	}
	payload := webAuthnSessionPayload{
		Ceremony: ceremony,
		UserID:   userID,
		Session:  *session,
	}
	raw, errMarshal := json.Marshal(payload)
	if errMarshal != nil {
		return "", errMarshal
	}
	expiresAt := session.Expires
	if expiresAt.IsZero() {
		expiresAt = time.Now().UTC().Add(5 * time.Minute)
	}
	record := &cluster.OAuthSessionRecord{
		State:     state,
		Provider:  webAuthnSessionProvider,
		Data:      cluster.JSONB(raw),
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
		ExpiresAt: expiresAt,
	}
	return state, h.repo.UpsertOAuthSession(ctx, record)
}

func (h *Handler) loadWebAuthnSession(ctx context.Context, state string, ceremony string, userID uint) (*webauthn.SessionData, error) {
	if h == nil || h.repo == nil {
		return nil, fmt.Errorf("user api repository is required")
	}
	state = strings.TrimSpace(state)
	if state == "" {
		return nil, fmt.Errorf("challenge id is required")
	}
	record, errRecord := h.repo.GetOAuthSession(ctx, state)
	if errRecord != nil {
		return nil, errRecord
	}
	if record == nil {
		return nil, fmt.Errorf("challenge not found")
	}
	if record.Provider != webAuthnSessionProvider {
		return nil, fmt.Errorf("invalid challenge")
	}
	if strings.TrimSpace(record.Status) != "" {
		return nil, fmt.Errorf("challenge is not active")
	}
	if !record.ExpiresAt.IsZero() && time.Now().UTC().After(record.ExpiresAt) {
		return nil, fmt.Errorf("challenge expired")
	}
	var payload webAuthnSessionPayload
	if errUnmarshal := json.Unmarshal([]byte(record.Data), &payload); errUnmarshal != nil {
		return nil, errUnmarshal
	}
	if payload.Ceremony != ceremony {
		return nil, fmt.Errorf("invalid challenge ceremony")
	}
	if payload.UserID != userID {
		return nil, fmt.Errorf("invalid challenge user")
	}
	return &payload.Session, nil
}

func webAuthnForRequest(c *gin.Context) (*webauthn.WebAuthn, error) {
	rpID, origin, errOrigin := webAuthnOrigin(c)
	if errOrigin != nil {
		return nil, errOrigin
	}
	return webauthn.New(&webauthn.Config{
		RPDisplayName: defaultTOTPIssuer,
		RPID:          rpID,
		RPOrigins:     []string{origin},
		AuthenticatorSelection: protocol.AuthenticatorSelection{
			UserVerification: protocol.VerificationRequired,
		},
	})
}

func webAuthnOrigin(c *gin.Context) (string, string, error) {
	origin := headerValue(c, "Origin")
	if origin != "" {
		parsed, errParse := url.Parse(origin)
		if errParse != nil || parsed == nil || parsed.Hostname() == "" || parsed.Scheme == "" {
			return "", "", fmt.Errorf("invalid origin")
		}
		return parsed.Hostname(), strings.TrimRight(origin, "/"), nil
	}
	host := firstNonEmpty(forwardedHeaderValue(c, "X-Forwarded-Host"), requestHost(c))
	if host == "" {
		return "", "", fmt.Errorf("request host is required")
	}
	proto := strings.ToLower(firstNonEmpty(forwardedHeaderValue(c, "X-Forwarded-Proto"), requestScheme(c)))
	if proto != "http" && proto != "https" {
		proto = "https"
	}
	rpID := hostWithoutPort(host)
	if rpID == "" {
		return "", "", fmt.Errorf("request host is required")
	}
	return rpID, proto + "://" + host, nil
}

func forwardedHeaderValue(c *gin.Context, key string) string {
	value := headerValue(c, key)
	if value == "" {
		return ""
	}
	if index := strings.Index(value, ","); index >= 0 {
		value = value[:index]
	}
	return strings.TrimSpace(value)
}

func requestHost(c *gin.Context) string {
	if c == nil || c.Request == nil {
		return ""
	}
	return strings.TrimSpace(c.Request.Host)
}

func requestScheme(c *gin.Context) string {
	if c == nil || c.Request == nil {
		return "https"
	}
	if c.Request.TLS != nil {
		return "https"
	}
	return "http"
}

func hostWithoutPort(host string) string {
	host = strings.TrimSpace(host)
	if host == "" {
		return ""
	}
	if parsed := strings.TrimSpace(host); strings.HasPrefix(parsed, "[") {
		if hostname, _, errSplit := net.SplitHostPort(parsed); errSplit == nil {
			return strings.Trim(hostname, "[]")
		}
		return strings.Trim(parsed, "[]")
	}
	if hostname, _, errSplit := net.SplitHostPort(host); errSplit == nil {
		return hostname
	}
	if index := strings.LastIndex(host, ":"); index > 0 && strings.Count(host, ":") == 1 {
		return host[:index]
	}
	return host
}

func passkeyCredentialPayload(raw []byte, credential json.RawMessage) json.RawMessage {
	if len(bytes.TrimSpace(credential)) > 0 {
		return compactRawJSON(credential)
	}
	raw = bytes.TrimSpace(raw)
	if len(raw) == 0 {
		return nil
	}
	var obj map[string]json.RawMessage
	if errUnmarshal := json.Unmarshal(raw, &obj); errUnmarshal != nil {
		return nil
	}
	if len(obj["id"]) > 0 && len(obj["response"]) > 0 {
		return compactRawJSON(raw)
	}
	return nil
}

func compactRawJSON(raw json.RawMessage) json.RawMessage {
	raw = bytes.TrimSpace(raw)
	if len(raw) == 0 {
		return nil
	}
	var buf bytes.Buffer
	if errCompact := json.Compact(&buf, raw); errCompact != nil {
		return append(json.RawMessage(nil), raw...)
	}
	return append(json.RawMessage(nil), buf.Bytes()...)
}
