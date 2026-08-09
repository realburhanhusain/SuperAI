package codex

// CodexTokenData holds the OAuth token information obtained from OpenAI.
// It includes the ID token, access token, refresh token, and associated user details.
type CodexTokenData struct {
	// IDToken is the JWT ID token containing user claims
	IDToken string `json:"id_token"`
	// AccessToken is the OAuth2 access token for API access
	AccessToken string `json:"access_token"`
	// RefreshToken is used to obtain new access tokens
	RefreshToken string `json:"refresh_token"`
	// AccountID is the OpenAI account identifier
	AccountID string `json:"account_id"`
	// Email is the OpenAI account email
	Email string `json:"email"`
	// Expire is the timestamp of the token expire
	Expire string `json:"expired"`
}
