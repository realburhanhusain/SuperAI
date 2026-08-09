package pluginauth

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/router-for-me/CLIProxyAPI/v7/sdk/pluginstore"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"golang.org/x/net/http/httpguts"
)

// ErrInvalidInput indicates that a plugin store authentication request failed validation.
var ErrInvalidInput = errors.New("invalid plugin store auth input")

type Service struct {
	repo *cluster.Repository
}

type CreateInput struct {
	Name        string
	Match       string
	ApplyTo     []string
	AuthType    string
	Token       pluginstore.Secret
	Username    pluginstore.Secret
	Password    pluginstore.Secret
	HeaderName  string
	HeaderValue pluginstore.Secret
	Enabled     *bool
}

type UpdateInput struct {
	Name        *string
	Match       *string
	ApplyTo     *[]string
	AuthType    *string
	Token       *pluginstore.Secret
	Username    *pluginstore.Secret
	Password    *pluginstore.Secret
	HeaderName  *string
	HeaderValue *pluginstore.Secret
	Enabled     *bool
}

func (i *CreateInput) clearSecrets() {
	if i == nil {
		return
	}
	i.Token.Clear()
	i.Username.Clear()
	i.Password.Clear()
	i.HeaderValue.Clear()
}

func (i *UpdateInput) clearSecrets() {
	if i == nil {
		return
	}
	clearSecretPointer(i.Token)
	clearSecretPointer(i.Username)
	clearSecretPointer(i.Password)
	clearSecretPointer(i.HeaderValue)
}

type Entry struct {
	ID                    uint     `json:"id"`
	Name                  string   `json:"name"`
	Match                 string   `json:"match"`
	ApplyTo               []string `json:"apply_to,omitempty"`
	AuthType              string   `json:"auth_type"`
	HeaderName            string   `json:"header_name,omitempty"`
	Enabled               bool     `json:"enabled"`
	Version               int64    `json:"version"`
	CredentialsConfigured bool     `json:"credentials_configured"`
}

type credentials struct {
	Token       pluginstore.Secret
	Username    pluginstore.Secret
	Password    pluginstore.Secret
	HeaderValue pluginstore.Secret
}

const (
	credentialPlaintextVersion = 1
	credentialPlaintextFields  = 4
)

func (c *credentials) Clear() {
	if c == nil {
		return
	}
	c.Token.Clear()
	c.Username.Clear()
	c.Password.Clear()
	c.HeaderValue.Clear()
}

func NewService(repo *cluster.Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) Create(ctx context.Context, input CreateInput) (Entry, error) {
	defer input.clearSecrets()
	if s == nil || s.repo == nil {
		return Entry{}, fmt.Errorf("plugin store auth service is unavailable")
	}
	enabled := true
	if input.Enabled != nil {
		enabled = *input.Enabled
	}
	authType := normalizeAuthType(input.AuthType)
	creds := credentials{
		Token:       cloneSecret(input.Token),
		Username:    cloneSecret(input.Username),
		Password:    cloneSecret(input.Password),
		HeaderValue: cloneSecret(input.HeaderValue),
	}
	defer creds.Clear()
	applyCredentialShape(authType, &creds)
	name, match, applyTo, headerName, errValidate := validateRule(input.Name, input.Match, input.ApplyTo, authType, input.HeaderName, creds)
	if errValidate != nil {
		return Entry{}, errValidate
	}
	applyToJSON, errApplyTo := json.Marshal(applyTo)
	if errApplyTo != nil {
		return Entry{}, errApplyTo
	}
	record := &cluster.PluginStoreAuthRecord{
		Name: name, Match: match, ApplyTo: cluster.JSONB(applyToJSON), AuthType: authType,
		HeaderName: headerName, Enabled: enabled,
	}
	key, keyVersion, errKey := s.repo.EnsurePluginStoreAuthKey(ctx)
	if errKey != nil {
		return Entry{}, errKey
	}
	defer clearBytes(key)
	if errCreate := s.repo.CreatePluginStoreAuth(ctx, record, func(id uint) ([]byte, int, error) {
		return encryptWithKey(id, authType, creds, key, keyVersion)
	}); errCreate != nil {
		return Entry{}, errCreate
	}
	defer clearBytes(record.EncryptedCredentials)
	return entryFromRecord(*record), nil
}

func (s *Service) List(ctx context.Context) ([]Entry, error) {
	if s == nil || s.repo == nil {
		return nil, fmt.Errorf("plugin store auth service is unavailable")
	}
	records, errRecords := s.repo.ListPluginStoreAuth(ctx)
	if errRecords != nil {
		return nil, errRecords
	}
	defer clearRecordCredentials(records)
	out := make([]Entry, 0, len(records))
	for index := range records {
		out = append(out, entryFromRecord(records[index]))
	}
	return out, nil
}

func (s *Service) Get(ctx context.Context, id uint) (Entry, error) {
	record, errRecord := s.repo.GetPluginStoreAuth(ctx, id)
	if errRecord != nil {
		return Entry{}, errRecord
	}
	defer clearBytes(record.EncryptedCredentials)
	return entryFromRecord(*record), nil
}

func (s *Service) Update(ctx context.Context, id uint, input UpdateInput) (Entry, error) {
	defer input.clearSecrets()
	if updateInputEmpty(input) {
		return s.Get(ctx, id)
	}
	record, creds, errRecord := s.getRecord(ctx, id)
	if errRecord != nil {
		return Entry{}, errRecord
	}
	defer creds.Clear()
	defer clearBytes(record.EncryptedCredentials)
	name := record.Name
	match := record.Match
	applyTo, errApplyTo := decodeApplyTo(record.ApplyTo)
	if errApplyTo != nil {
		return Entry{}, errApplyTo
	}
	authType := normalizeAuthType(record.AuthType)
	headerName := record.HeaderName
	enabled := record.Enabled
	if input.Name != nil {
		name = *input.Name
	}
	if input.Match != nil {
		match = *input.Match
	}
	if input.ApplyTo != nil {
		applyTo = append([]string(nil), (*input.ApplyTo)...)
	}
	if input.AuthType != nil {
		nextType := normalizeAuthType(*input.AuthType)
		if nextType != authType {
			creds.Clear()
		}
		authType = nextType
	}
	if input.HeaderName != nil {
		headerName = *input.HeaderName
	}
	if input.Enabled != nil {
		enabled = *input.Enabled
	}
	setSecret(&creds.Token, input.Token)
	setSecret(&creds.Username, input.Username)
	setSecret(&creds.Password, input.Password)
	setSecret(&creds.HeaderValue, input.HeaderValue)
	applyCredentialShape(authType, &creds)
	name, match, applyTo, headerName, errValidate := validateRule(name, match, applyTo, authType, headerName, creds)
	if errValidate != nil {
		return Entry{}, errValidate
	}
	encrypted, keyVersion, errEncrypt := s.encrypt(ctx, record.ID, authType, creds)
	if errEncrypt != nil {
		return Entry{}, errEncrypt
	}
	defer clearBytes(encrypted)
	applyToJSON, errMarshal := json.Marshal(applyTo)
	if errMarshal != nil {
		return Entry{}, errMarshal
	}
	record.Name = name
	record.Match = match
	record.ApplyTo = cluster.JSONB(applyToJSON)
	record.AuthType = authType
	record.HeaderName = headerName
	record.EncryptedCredentials = encrypted
	record.KeyVersion = keyVersion
	record.Enabled = enabled
	if errUpdate := s.repo.UpdatePluginStoreAuth(ctx, record); errUpdate != nil {
		return Entry{}, errUpdate
	}
	return entryFromRecord(*record), nil
}

func (s *Service) Delete(ctx context.Context, id uint) error {
	if s == nil || s.repo == nil {
		return fmt.Errorf("plugin store auth service is unavailable")
	}
	return s.repo.DeletePluginStoreAuth(ctx, id)
}

func (s *Service) Resolved(ctx context.Context) ([]pluginstore.ResolvedAuthConfig, error) {
	if s == nil || s.repo == nil {
		return nil, fmt.Errorf("plugin store auth service is unavailable")
	}
	records, errRecords := s.repo.ListPluginStoreAuth(ctx)
	if errRecords != nil {
		return nil, errRecords
	}
	defer clearRecordCredentials(records)
	out := make([]pluginstore.ResolvedAuthConfig, 0, len(records))
	var key []byte
	var keyVersion int
	keyLoaded := false
	defer func() { clearBytes(key) }()
	for index := range records {
		if !records[index].Enabled {
			continue
		}
		if normalizeAuthType(records[index].AuthType) != pluginstore.AuthTypeNone && !keyLoaded {
			var errKey error
			key, keyVersion, errKey = s.repo.EnsurePluginStoreAuthKey(ctx)
			if errKey != nil {
				pluginstore.ClearResolvedAuthConfigs(out)
				return nil, errKey
			}
			keyLoaded = true
		}
		creds, errDecrypt := decryptWithKey(records[index], key, keyVersion)
		if errDecrypt != nil {
			pluginstore.ClearResolvedAuthConfigs(out)
			return nil, errDecrypt
		}
		applyTo, errApplyTo := decodeApplyTo(records[index].ApplyTo)
		if errApplyTo != nil {
			creds.Clear()
			pluginstore.ClearResolvedAuthConfigs(out)
			return nil, errApplyTo
		}
		item := pluginstore.ResolvedAuthConfig{
			Match: records[index].Match, ApplyTo: applyTo, Type: records[index].AuthType,
			Token: creds.Token, Username: creds.Username, Password: creds.Password,
			HeaderName: records[index].HeaderName, HeaderValue: creds.HeaderValue,
		}
		creds = credentials{}
		if errValidate := validateResolvedAuthHeaders(item); errValidate != nil {
			item.Clear()
			pluginstore.ClearResolvedAuthConfigs(out)
			return nil, fmt.Errorf("plugin store auth %d: %w", records[index].ID, errValidate)
		}
		if errValidate := pluginstore.ValidateResolvedAuthConfig(item); errValidate != nil {
			item.Clear()
			pluginstore.ClearResolvedAuthConfigs(out)
			return nil, fmt.Errorf("plugin store auth %d: %w", records[index].ID, errValidate)
		}
		out = append(out, item)
	}
	return out, nil
}

func (s *Service) getRecord(ctx context.Context, id uint) (*cluster.PluginStoreAuthRecord, credentials, error) {
	if s == nil || s.repo == nil {
		return nil, credentials{}, fmt.Errorf("plugin store auth service is unavailable")
	}
	record, errRecord := s.repo.GetPluginStoreAuth(ctx, id)
	if errRecord != nil {
		return nil, credentials{}, errRecord
	}
	creds, errDecrypt := s.decrypt(ctx, *record)
	if errDecrypt != nil {
		clearBytes(record.EncryptedCredentials)
		return nil, credentials{}, errDecrypt
	}
	return record, creds, nil
}

func (s *Service) encrypt(ctx context.Context, id uint, authType string, creds credentials) ([]byte, int, error) {
	key, keyVersion, errKey := s.repo.EnsurePluginStoreAuthKey(ctx)
	if errKey != nil {
		return nil, 0, errKey
	}
	defer clearBytes(key)
	return encryptWithKey(id, authType, creds, key, keyVersion)
}

func encryptWithKey(id uint, authType string, creds credentials, key []byte, keyVersion int) ([]byte, int, error) {
	if normalizeAuthType(authType) == pluginstore.AuthTypeNone {
		return nil, keyVersion, nil
	}
	raw, errEncode := encodeCredentialPlaintext(creds)
	if errEncode != nil {
		return nil, 0, errEncode
	}
	defer clearBytes(raw)
	block, errBlock := aes.NewCipher(key)
	if errBlock != nil {
		return nil, 0, errBlock
	}
	gcm, errGCM := cipher.NewGCM(block)
	if errGCM != nil {
		return nil, 0, errGCM
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, errRandom := rand.Read(nonce); errRandom != nil {
		return nil, 0, errRandom
	}
	aad := credentialAAD(id, authType, keyVersion)
	return gcm.Seal(nonce, nonce, raw, aad), keyVersion, nil
}

func (s *Service) decrypt(ctx context.Context, record cluster.PluginStoreAuthRecord) (credentials, error) {
	if normalizeAuthType(record.AuthType) == pluginstore.AuthTypeNone {
		return decryptWithKey(record, nil, 0)
	}
	key, keyVersion, errKey := s.repo.EnsurePluginStoreAuthKey(ctx)
	if errKey != nil {
		return credentials{}, errKey
	}
	defer clearBytes(key)
	return decryptWithKey(record, key, keyVersion)
}

func decryptWithKey(record cluster.PluginStoreAuthRecord, key []byte, keyVersion int) (credentials, error) {
	if normalizeAuthType(record.AuthType) == pluginstore.AuthTypeNone {
		if len(record.EncryptedCredentials) != 0 {
			return credentials{}, fmt.Errorf("plugin store auth none credentials are invalid")
		}
		return credentials{}, nil
	}
	if record.KeyVersion != keyVersion {
		return credentials{}, fmt.Errorf("plugin store auth key version %d is unsupported", record.KeyVersion)
	}
	block, errBlock := aes.NewCipher(key)
	if errBlock != nil {
		return credentials{}, errBlock
	}
	gcm, errGCM := cipher.NewGCM(block)
	if errGCM != nil {
		return credentials{}, errGCM
	}
	if len(record.EncryptedCredentials) < gcm.NonceSize() {
		return credentials{}, fmt.Errorf("plugin store auth credentials are invalid")
	}
	nonce := record.EncryptedCredentials[:gcm.NonceSize()]
	ciphertext := record.EncryptedCredentials[gcm.NonceSize():]
	aad := credentialAAD(record.ID, record.AuthType, record.KeyVersion)
	raw, errOpen := gcm.Open(nil, nonce, ciphertext, aad)
	if errOpen != nil {
		return credentials{}, fmt.Errorf("decrypt plugin store auth credentials: %w", errOpen)
	}
	defer clearBytes(raw)
	creds, errDecode := decodeCredentialPlaintext(raw)
	if errDecode != nil {
		return credentials{}, fmt.Errorf("decode plugin store auth credentials: %w", errDecode)
	}
	return creds, nil
}

func encodeCredentialPlaintext(creds credentials) ([]byte, error) {
	fields := []pluginstore.Secret{creds.Token, creds.Username, creds.Password, creds.HeaderValue}
	total := 1 + credentialPlaintextFields*4
	maxInt := int(^uint(0) >> 1)
	const maxUint32 = uint64(^uint32(0))
	for _, field := range fields {
		if uint64(len(field)) > maxUint32 {
			return nil, fmt.Errorf("plugin store auth credential field is too large")
		}
		if len(field) > maxInt-total {
			return nil, fmt.Errorf("plugin store auth credentials are too large")
		}
		total += len(field)
	}
	raw := make([]byte, total)
	raw[0] = credentialPlaintextVersion
	offset := 1
	for _, field := range fields {
		binary.BigEndian.PutUint32(raw[offset:offset+4], uint32(len(field)))
		offset += 4
		copy(raw[offset:offset+len(field)], field)
		offset += len(field)
	}
	return raw, nil
}

func decodeCredentialPlaintext(raw []byte) (credentials, error) {
	minimumSize := 1 + credentialPlaintextFields*4
	if len(raw) < minimumSize || raw[0] != credentialPlaintextVersion {
		return credentials{}, fmt.Errorf("plugin store auth credential encoding is invalid")
	}
	var creds credentials
	fields := []*pluginstore.Secret{&creds.Token, &creds.Username, &creds.Password, &creds.HeaderValue}
	offset := 1
	for _, field := range fields {
		if len(raw)-offset < 4 {
			creds.Clear()
			return credentials{}, fmt.Errorf("plugin store auth credential encoding is truncated")
		}
		length := uint64(binary.BigEndian.Uint32(raw[offset : offset+4]))
		offset += 4
		if length > uint64(len(raw)-offset) {
			creds.Clear()
			return credentials{}, fmt.Errorf("plugin store auth credential encoding is truncated")
		}
		end := offset + int(length)
		*field = append(pluginstore.Secret(nil), raw[offset:end]...)
		offset = end
	}
	if offset != len(raw) {
		creds.Clear()
		return credentials{}, fmt.Errorf("plugin store auth credential encoding has trailing data")
	}
	return creds, nil
}

func validateRule(name, match string, applyTo []string, authType, headerName string, creds credentials) (string, string, []string, string, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return "", "", nil, "", invalidInput(fmt.Errorf("plugin store auth name is required"))
	}
	match = strings.TrimSpace(match)
	authType = normalizeAuthType(authType)
	headerName = strings.TrimSpace(headerName)
	if authType != pluginstore.AuthTypeHeader {
		headerName = ""
	}
	applyTo = normalizeApplyTo(applyTo)
	item := pluginstore.ResolvedAuthConfig{
		Match: match, ApplyTo: applyTo, Type: authType,
		Token: creds.Token, Username: creds.Username, Password: creds.Password,
		HeaderName: headerName, HeaderValue: creds.HeaderValue,
	}
	if errHeaders := validateResolvedAuthHeaders(item); errHeaders != nil {
		return "", "", nil, "", invalidInput(errHeaders)
	}
	if errValidate := pluginstore.ValidateResolvedAuthConfig(item); errValidate != nil {
		return "", "", nil, "", invalidInput(errValidate)
	}
	return name, match, applyTo, headerName, nil
}

func validateResolvedAuthHeaders(item pluginstore.ResolvedAuthConfig) error {
	authType := normalizeAuthType(item.Type)
	if authType == pluginstore.AuthTypeHeader && !httpguts.ValidHeaderFieldName(item.HeaderName) {
		return fmt.Errorf("plugin store resolved auth header name is invalid")
	}
	if (authType == pluginstore.AuthTypeBearer || authType == pluginstore.AuthTypeGitHubToken) && !validHTTPHeaderValue(item.Token) {
		return fmt.Errorf("plugin store resolved auth token is invalid")
	}
	if authType == pluginstore.AuthTypeHeader && !validHTTPHeaderValue(item.HeaderValue) {
		return fmt.Errorf("plugin store resolved auth header value is invalid")
	}
	return nil
}

func validHTTPHeaderValue(value []byte) bool {
	for _, current := range value {
		if current == 0x7f || (current < 0x20 && current != '\t') {
			return false
		}
	}
	return true
}

func invalidInput(err error) error {
	if err == nil {
		return nil
	}
	return fmt.Errorf("%w: %v", ErrInvalidInput, err)
}

func normalizeAuthType(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	if value == "" {
		return pluginstore.AuthTypeNone
	}
	return value
}

func normalizeApplyTo(values []string) []string {
	out := make([]string, 0, len(values))
	seen := map[string]struct{}{}
	for _, value := range values {
		value = strings.ToLower(strings.TrimSpace(value))
		if value == "" {
			continue
		}
		if _, exists := seen[value]; exists {
			continue
		}
		seen[value] = struct{}{}
		out = append(out, value)
	}
	return out
}

func applyCredentialShape(authType string, creds *credentials) {
	if creds == nil {
		return
	}
	switch normalizeAuthType(authType) {
	case pluginstore.AuthTypeBearer, pluginstore.AuthTypeGitHubToken:
		creds.Username.Clear()
		creds.Password.Clear()
		creds.HeaderValue.Clear()
	case pluginstore.AuthTypeBasic:
		creds.Token.Clear()
		creds.HeaderValue.Clear()
	case pluginstore.AuthTypeHeader:
		creds.Token.Clear()
		creds.Username.Clear()
		creds.Password.Clear()
	default:
		creds.Clear()
	}
}

func setSecret(target *pluginstore.Secret, value *pluginstore.Secret) {
	if target == nil || value == nil {
		return
	}
	target.Clear()
	*target = cloneSecret(*value)
}

func cloneSecret(value pluginstore.Secret) pluginstore.Secret {
	return append(pluginstore.Secret(nil), value...)
}

func clearSecretPointer(value *pluginstore.Secret) {
	if value != nil {
		value.Clear()
	}
}

func updateInputEmpty(input UpdateInput) bool {
	return input.Name == nil && input.Match == nil && input.ApplyTo == nil && input.AuthType == nil &&
		input.Token == nil && input.Username == nil && input.Password == nil && input.HeaderName == nil &&
		input.HeaderValue == nil && input.Enabled == nil
}

func decodeApplyTo(raw cluster.JSONB) ([]string, error) {
	if len(raw) == 0 {
		return nil, nil
	}
	var values []string
	if errUnmarshal := json.Unmarshal(raw, &values); errUnmarshal != nil {
		return nil, fmt.Errorf("decode plugin store auth apply_to: %w", errUnmarshal)
	}
	return normalizeApplyTo(values), nil
}

func entryFromRecord(record cluster.PluginStoreAuthRecord) Entry {
	applyTo, _ := decodeApplyTo(record.ApplyTo)
	return Entry{
		ID: record.ID, Name: record.Name, Match: record.Match, ApplyTo: applyTo,
		AuthType: record.AuthType, HeaderName: record.HeaderName, Enabled: record.Enabled, Version: record.Version,
		CredentialsConfigured: normalizeAuthType(record.AuthType) != pluginstore.AuthTypeNone && len(record.EncryptedCredentials) > 0,
	}
}

func credentialAAD(id uint, authType string, keyVersion int) []byte {
	return []byte(fmt.Sprintf("%d\x00%s\x00%d", id, normalizeAuthType(authType), keyVersion))
}

func clearBytes(value []byte) {
	for index := range value {
		value[index] = 0
	}
}

func clearRecordCredentials(records []cluster.PluginStoreAuthRecord) {
	for index := range records {
		clearBytes(records[index].EncryptedCredentials)
		records[index].EncryptedCredentials = nil
	}
}
