package xai

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
)

// GeneratePKCECodes creates a verifier/challenge pair for the OAuth flow.
func GeneratePKCECodes() (*PKCECodes, error) {
	bytes := make([]byte, 96)
	if _, errRead := rand.Read(bytes); errRead != nil {
		return nil, fmt.Errorf("xai pkce: generate verifier: %w", errRead)
	}
	verifier := base64.URLEncoding.WithPadding(base64.NoPadding).EncodeToString(bytes)
	hash := sha256.Sum256([]byte(verifier))
	challenge := base64.URLEncoding.WithPadding(base64.NoPadding).EncodeToString(hash[:])
	return &PKCECodes{CodeVerifier: verifier, CodeChallenge: challenge}, nil
}
