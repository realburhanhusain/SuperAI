package claude

// ClaudeTokenData holds OAuth token information from Anthropic
type ClaudeTokenData struct {
	// AccessToken is the OAuth2 access token for API access
	AccessToken string `json:"access_token"`
	// RefreshToken is used to obtain new access tokens
	RefreshToken string `json:"refresh_token"`
	// Email is the Anthropic account email
	Email string `json:"email"`
	// Expire is the timestamp of the token expire
	Expire string `json:"expired"`
}
