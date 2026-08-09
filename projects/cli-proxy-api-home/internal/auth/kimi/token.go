package kimi

// KimiTokenData holds the raw OAuth token response from Kimi.
type KimiTokenData struct {
	// AccessToken is the OAuth2 access token.
	AccessToken string `json:"access_token"`
	// RefreshToken is the OAuth2 refresh token.
	RefreshToken string `json:"refresh_token"`
	// TokenType is the type of token, typically "Bearer".
	TokenType string `json:"token_type"`
	// ExpiresAt is the Unix timestamp when the token expires.
	ExpiresAt int64 `json:"expires_at"`
	// Scope is the OAuth2 scope granted to the token.
	Scope string `json:"scope"`
}
