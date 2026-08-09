package userapi

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha1"
	"crypto/subtle"
	"encoding/base32"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
)

const (
	defaultTOTPIssuer    = "CLIProxyAPIHome"
	defaultTOTPPeriod    = 30
	defaultTOTPDigits    = 6
	defaultTOTPAlgorithm = "SHA1"
	totpSecretBytes      = 20
)

type mfaSettings struct {
	Enabled   bool          `json:"enabled,omitempty"`
	Secret    string        `json:"secret,omitempty"`
	Period    int           `json:"period,omitempty"`
	Digits    int           `json:"digits,omitempty"`
	Algorithm string        `json:"algorithm,omitempty"`
	TOTP      *totpSettings `json:"totp,omitempty"`
}

type totpSettings struct {
	Enabled   bool       `json:"enabled"`
	Secret    string     `json:"secret"`
	Issuer    string     `json:"issuer,omitempty"`
	Account   string     `json:"account,omitempty"`
	Period    int        `json:"period,omitempty"`
	Digits    int        `json:"digits,omitempty"`
	Algorithm string     `json:"algorithm,omitempty"`
	BoundAt   *time.Time `json:"bound_at,omitempty"`
}

func loadTOTP(raw cluster.JSONB) (*totpSettings, bool) {
	if len(raw) == 0 || strings.EqualFold(strings.TrimSpace(string(raw)), "null") {
		return nil, false
	}
	var settings mfaSettings
	if errUnmarshal := json.Unmarshal(raw, &settings); errUnmarshal != nil {
		return nil, false
	}
	if settings.TOTP != nil && settings.TOTP.Enabled && strings.TrimSpace(settings.TOTP.Secret) != "" {
		next := normalizeTOTPSettings(*settings.TOTP)
		return &next, true
	}
	if settings.Enabled && strings.TrimSpace(settings.Secret) != "" {
		next := normalizeTOTPSettings(totpSettings{
			Enabled:   true,
			Secret:    settings.Secret,
			Period:    settings.Period,
			Digits:    settings.Digits,
			Algorithm: settings.Algorithm,
		})
		return &next, true
	}
	return nil, false
}

func marshalTOTP(username string, secret string, issuer string) (cluster.JSONB, error) {
	now := time.Now().UTC()
	settings := mfaSettings{
		Enabled: true,
		TOTP: &totpSettings{
			Enabled:   true,
			Secret:    normalizeTOTPSecret(secret),
			Issuer:    normalizeTOTPIssuer(issuer),
			Account:   strings.TrimSpace(username),
			Period:    defaultTOTPPeriod,
			Digits:    defaultTOTPDigits,
			Algorithm: defaultTOTPAlgorithm,
			BoundAt:   &now,
		},
	}
	raw, errMarshal := json.Marshal(settings)
	if errMarshal != nil {
		return nil, errMarshal
	}
	return cluster.JSONB(raw), nil
}

func normalizeTOTPSettings(settings totpSettings) totpSettings {
	settings.Secret = normalizeTOTPSecret(settings.Secret)
	settings.Issuer = normalizeTOTPIssuer(settings.Issuer)
	if settings.Period <= 0 {
		settings.Period = defaultTOTPPeriod
	}
	if settings.Digits <= 0 {
		settings.Digits = defaultTOTPDigits
	}
	if strings.TrimSpace(settings.Algorithm) == "" {
		settings.Algorithm = defaultTOTPAlgorithm
	}
	return settings
}

func normalizeTOTPIssuer(issuer string) string {
	issuer = strings.TrimSpace(issuer)
	if issuer == "" {
		return defaultTOTPIssuer
	}
	return issuer
}

func generateTOTPSecret() (string, error) {
	buf := make([]byte, totpSecretBytes)
	if _, errRead := rand.Read(buf); errRead != nil {
		return "", errRead
	}
	return base32.StdEncoding.WithPadding(base32.NoPadding).EncodeToString(buf), nil
}

func verifyTOTPCode(secret string, code string, now time.Time) bool {
	secret = normalizeTOTPSecret(secret)
	code = normalizeTOTPCode(code)
	if secret == "" || code == "" {
		return false
	}
	counter := now.UTC().Unix() / int64(defaultTOTPPeriod)
	for offset := int64(-1); offset <= 1; offset++ {
		expected, errCode := hotpCode(secret, counter+offset)
		if errCode != nil {
			return false
		}
		if subtle.ConstantTimeCompare([]byte(expected), []byte(code)) == 1 {
			return true
		}
	}
	return false
}

func hotpCode(secret string, counter int64) (string, error) {
	key, errSecret := decodeTOTPSecret(secret)
	if errSecret != nil {
		return "", errSecret
	}
	var msg [8]byte
	binary.BigEndian.PutUint64(msg[:], uint64(counter))
	mac := hmac.New(sha1.New, key)
	if _, errWrite := mac.Write(msg[:]); errWrite != nil {
		return "", errWrite
	}
	sum := mac.Sum(nil)
	offset := sum[len(sum)-1] & 0x0f
	binCode := (uint32(sum[offset])&0x7f)<<24 |
		(uint32(sum[offset+1])&0xff)<<16 |
		(uint32(sum[offset+2])&0xff)<<8 |
		(uint32(sum[offset+3]) & 0xff)
	mod := uint32(1)
	for i := 0; i < defaultTOTPDigits; i++ {
		mod *= 10
	}
	return fmt.Sprintf("%0"+strconv.Itoa(defaultTOTPDigits)+"d", binCode%mod), nil
}

func decodeTOTPSecret(secret string) ([]byte, error) {
	secret = normalizeTOTPSecret(secret)
	if secret == "" {
		return nil, fmt.Errorf("totp secret is required")
	}
	return base32.StdEncoding.WithPadding(base32.NoPadding).DecodeString(secret)
}

func normalizeTOTPSecret(secret string) string {
	secret = strings.ToUpper(strings.TrimSpace(secret))
	secret = strings.ReplaceAll(secret, " ", "")
	secret = strings.ReplaceAll(secret, "-", "")
	secret = strings.TrimRight(secret, "=")
	return secret
}

func normalizeTOTPCode(code string) string {
	code = strings.TrimSpace(code)
	code = strings.ReplaceAll(code, " ", "")
	return code
}

func otpauthURL(username string, secret string, issuer string) string {
	issuer = normalizeTOTPIssuer(issuer)
	username = strings.TrimSpace(username)
	label := issuer
	if username != "" {
		label += ":" + username
	}
	values := url.Values{}
	values.Set("secret", normalizeTOTPSecret(secret))
	values.Set("issuer", issuer)
	values.Set("algorithm", defaultTOTPAlgorithm)
	values.Set("digits", strconv.Itoa(defaultTOTPDigits))
	values.Set("period", strconv.Itoa(defaultTOTPPeriod))
	return "otpauth://totp/" + url.PathEscape(label) + "?" + values.Encode()
}
