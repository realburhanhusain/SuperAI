package kimi

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/config"
	log "github.com/sirupsen/logrus"
)

const (
	kimiDeviceCodeURL   = kimiOAuthHost + "/api/oauth/device_authorization"
	defaultPollInterval = 5 * time.Second
	maxPollDuration     = 15 * time.Minute
)

type KimiAuth struct {
	deviceClient *DeviceFlowClient
}

type KimiAuthBundle struct {
	TokenData *KimiTokenData
	DeviceID  string
}

type DeviceCodeResponse struct {
	DeviceCode              string `json:"device_code"`
	UserCode                string `json:"user_code"`
	VerificationURI         string `json:"verification_uri,omitempty"`
	VerificationURIComplete string `json:"verification_uri_complete"`
	ExpiresIn               int    `json:"expires_in"`
	Interval                int    `json:"interval"`
}

// NewKimiAuth creates a new kimi auth.
func NewKimiAuth(cfg *config.Config) *KimiAuth {
	return &KimiAuth{deviceClient: NewDeviceFlowClient(cfg)}
}

// NewDeviceFlowClient creates a new device flow client.
func NewDeviceFlowClient(cfg *config.Config) *DeviceFlowClient {
	return NewDeviceFlowClientWithDeviceID(cfg, "")
}

// NewDeviceFlowClientWithDeviceID creates a new device flow client with device id.
func NewDeviceFlowClientWithDeviceID(cfg *config.Config, deviceID string) *DeviceFlowClient {
	return NewDeviceFlowClientWithDeviceIDAndProxyURL(cfg, deviceID, "")
}

// StartDeviceFlow starts a device flow.
func (k *KimiAuth) StartDeviceFlow(ctx context.Context) (*DeviceCodeResponse, error) {
	if k == nil || k.deviceClient == nil {
		return nil, fmt.Errorf("kimi: client not ready")
	}
	return k.deviceClient.RequestDeviceCode(ctx)
}

// WaitForAuthorization returns a wait for authorization.
func (k *KimiAuth) WaitForAuthorization(ctx context.Context, deviceCode *DeviceCodeResponse) (*KimiAuthBundle, error) {
	if k == nil || k.deviceClient == nil {
		return nil, fmt.Errorf("kimi: client not ready")
	}
	tokenData, errToken := k.deviceClient.PollForToken(ctx, deviceCode)
	if errToken != nil {
		return nil, errToken
	}
	return &KimiAuthBundle{
		TokenData: tokenData,
		DeviceID:  k.deviceClient.deviceID,
	}, nil
}

// RequestDeviceCode handles request device code.
func (c *DeviceFlowClient) RequestDeviceCode(ctx context.Context) (*DeviceCodeResponse, error) {
	// Validate request inputs before mutating persisted state.
	if c == nil || c.httpClient == nil {
		return nil, fmt.Errorf("kimi: client not ready")
	}
	if ctx == nil {
		ctx = context.Background()
	}

	data := url.Values{}
	data.Set("client_id", kimiClientID)

	req, errRequest := http.NewRequestWithContext(ctx, http.MethodPost, kimiDeviceCodeURL, strings.NewReader(data.Encode()))
	if errRequest != nil {
		return nil, fmt.Errorf("kimi: failed to create device code request: %w", errRequest)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Accept", "application/json")
	for k, v := range c.commonHeaders() {
		req.Header.Set(k, v)
	}

	resp, errDo := c.httpClient.Do(req)
	if errDo != nil {
		return nil, fmt.Errorf("kimi: device code request failed: %w", errDo)
	}
	defer func() {
		if errClose := resp.Body.Close(); errClose != nil {
			log.Errorf("kimi device code: response body close error: %v", errClose)
		}
	}()

	bodyBytes, errRead := io.ReadAll(resp.Body)
	if errRead != nil {
		return nil, fmt.Errorf("kimi: failed to read device code response: %w", errRead)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("kimi: device code request failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var deviceCode DeviceCodeResponse
	if errUnmarshal := json.Unmarshal(bodyBytes, &deviceCode); errUnmarshal != nil {
		return nil, fmt.Errorf("kimi: failed to parse device code response: %w", errUnmarshal)
	}
	return &deviceCode, nil
}

// PollForToken converts poll for token.
func (c *DeviceFlowClient) PollForToken(ctx context.Context, deviceCode *DeviceCodeResponse) (*KimiTokenData, error) {
	// Resolve credential context before calling upstream OAuth services.
	if c == nil || c.httpClient == nil {
		return nil, fmt.Errorf("kimi: client not ready")
	}
	if ctx == nil {
		ctx = context.Background()
	}
	if deviceCode == nil {
		return nil, fmt.Errorf("kimi: device code is nil")
	}

	interval := time.Duration(deviceCode.Interval) * time.Second
	if interval < defaultPollInterval {
		interval = defaultPollInterval
	}

	deadline := time.Now().Add(maxPollDuration)
	if deviceCode.ExpiresIn > 0 {
		codeDeadline := time.Now().Add(time.Duration(deviceCode.ExpiresIn) * time.Second)
		if codeDeadline.Before(deadline) {
			deadline = codeDeadline
		}
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("kimi: context cancelled: %w", ctx.Err())
		case <-ticker.C:
			if time.Now().After(deadline) {
				return nil, fmt.Errorf("kimi: device code expired")
			}
			token, errPoll, shouldContinue := c.exchangeDeviceCode(ctx, deviceCode.DeviceCode)
			if token != nil {
				return token, nil
			}
			if !shouldContinue {
				return nil, errPoll
			}
		}
	}
}

// exchangeDeviceCode handles an exchange device code.
func (c *DeviceFlowClient) exchangeDeviceCode(ctx context.Context, deviceCode string) (*KimiTokenData, error, bool) {
	// Keep validation before state changes so failures leave existing data intact.
	data := url.Values{}
	data.Set("client_id", kimiClientID)
	data.Set("device_code", strings.TrimSpace(deviceCode))
	data.Set("grant_type", "urn:ietf:params:oauth:grant-type:device_code")

	req, errRequest := http.NewRequestWithContext(ctx, http.MethodPost, kimiTokenURL, strings.NewReader(data.Encode()))
	if errRequest != nil {
		return nil, fmt.Errorf("kimi: failed to create token request: %w", errRequest), false
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Accept", "application/json")
	for k, v := range c.commonHeaders() {
		req.Header.Set(k, v)
	}

	resp, errDo := c.httpClient.Do(req)
	if errDo != nil {
		return nil, fmt.Errorf("kimi: token request failed: %w", errDo), false
	}
	defer func() {
		if errClose := resp.Body.Close(); errClose != nil {
			log.Errorf("kimi token exchange: response body close error: %v", errClose)
		}
	}()

	bodyBytes, errRead := io.ReadAll(resp.Body)
	if errRead != nil {
		return nil, fmt.Errorf("kimi: failed to read token response: %w", errRead), false
	}

	var oauthResp struct {
		Error            string  `json:"error"`
		ErrorDescription string  `json:"error_description"`
		AccessToken      string  `json:"access_token"`
		RefreshToken     string  `json:"refresh_token"`
		TokenType        string  `json:"token_type"`
		ExpiresIn        float64 `json:"expires_in"`
		Scope            string  `json:"scope"`
	}
	if errUnmarshal := json.Unmarshal(bodyBytes, &oauthResp); errUnmarshal != nil {
		return nil, fmt.Errorf("kimi: failed to parse token response: %w", errUnmarshal), false
	}

	if oauthResp.Error != "" {
		switch oauthResp.Error {
		case "authorization_pending", "slow_down":
			return nil, nil, true
		case "expired_token":
			return nil, fmt.Errorf("kimi: device code expired"), false
		case "access_denied":
			return nil, fmt.Errorf("kimi: access denied by user"), false
		default:
			return nil, fmt.Errorf("kimi: OAuth error: %s - %s", oauthResp.Error, oauthResp.ErrorDescription), false
		}
	}
	if oauthResp.AccessToken == "" {
		return nil, fmt.Errorf("kimi: empty access token in response"), false
	}

	var expiresAt int64
	if oauthResp.ExpiresIn > 0 {
		expiresAt = time.Now().Unix() + int64(oauthResp.ExpiresIn)
	}
	return &KimiTokenData{
		AccessToken:  oauthResp.AccessToken,
		RefreshToken: oauthResp.RefreshToken,
		TokenType:    oauthResp.TokenType,
		ExpiresAt:    expiresAt,
		Scope:        oauthResp.Scope,
	}, nil, false
}
