package cluster

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"gorm.io/gorm"
)

const (
	OAuthSessionTTL          = 20 * time.Minute
	oauthCompletedSessionTTL = time.Minute
)

// ErrOAuthSessionNotPending reports that session data can no longer be changed.
var ErrOAuthSessionNotPending = errors.New("oauth session is not pending")

// NewOAuthSessionRecord creates a new o auth session record.
func NewOAuthSessionRecord(provider, state string, data map[string]any, now time.Time) (*OAuthSessionRecord, error) {
	// Resolve credential context before calling upstream OAuth services.
	provider = strings.ToLower(strings.TrimSpace(provider))
	state = strings.TrimSpace(state)
	if provider == "" {
		return nil, fmt.Errorf("oauth provider is required")
	}
	if state == "" {
		return nil, fmt.Errorf("oauth state is required")
	}
	if now.IsZero() {
		now = time.Now().UTC()
	}
	rawData, errMarshal := json.Marshal(data)
	if errMarshal != nil {
		return nil, errMarshal
	}
	return &OAuthSessionRecord{
		State:     state,
		Provider:  provider,
		Data:      JSONB(rawData),
		CreatedAt: now,
		UpdatedAt: now,
		ExpiresAt: now.Add(OAuthSessionTTL),
	}, nil
}

// OAuthSessionData handles an o auth session data.
func OAuthSessionData(record *OAuthSessionRecord) (map[string]any, error) {
	if record == nil || len(record.Data) == 0 {
		return nil, nil
	}
	var data map[string]any
	if errUnmarshal := json.Unmarshal([]byte(record.Data), &data); errUnmarshal != nil {
		return nil, errUnmarshal
	}
	return data, nil
}

// UpsertOAuthSession inserts or updates an o auth session.
func (r *Repository) UpsertOAuthSession(ctx context.Context, record *OAuthSessionRecord) error {
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	if record == nil {
		return fmt.Errorf("oauth session record is nil")
	}
	if strings.TrimSpace(record.State) == "" {
		return fmt.Errorf("oauth state is required")
	}
	if record.CreatedAt.IsZero() {
		record.CreatedAt = time.Now().UTC()
	}
	record.UpdatedAt = time.Now().UTC()
	if record.ExpiresAt.IsZero() {
		record.ExpiresAt = record.UpdatedAt.Add(OAuthSessionTTL)
	}
	if errDelete := deleteExpiredCompletedOAuthSessions(ctx, db, time.Now().UTC()); errDelete != nil {
		return errDelete
	}
	return db.WithContext(contextOrBackground(ctx)).Save(record).Error
}

// GetOAuthSession returns an o auth session.
func (r *Repository) GetOAuthSession(ctx context.Context, state string) (*OAuthSessionRecord, error) {
	// Resolve credential context before calling upstream OAuth services.
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}
	state = strings.TrimSpace(state)
	if state == "" {
		return nil, fmt.Errorf("oauth state is required")
	}
	record := &OAuthSessionRecord{}
	errFirst := db.WithContext(contextOrBackground(ctx)).Where("state = ?", state).First(record).Error
	if errors.Is(errFirst, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	if errFirst != nil {
		return nil, errFirst
	}
	now := time.Now().UTC()
	if !record.ExpiresAt.IsZero() && !record.ExpiresAt.After(now) && strings.EqualFold(record.Status, "complete") {
		if errDelete := deleteExpiredCompletedOAuthSessions(ctx, db, now); errDelete != nil {
			return nil, errDelete
		}
		return nil, nil
	}
	if !record.ExpiresAt.IsZero() && !record.ExpiresAt.After(now) && record.Status == "" {
		record.Status = "error"
		record.Error = "OAuth flow timed out"
		record.UpdatedAt = now
		if errSave := db.WithContext(contextOrBackground(ctx)).Save(record).Error; errSave != nil {
			return nil, errSave
		}
	}
	return record, nil
}

func deleteExpiredCompletedOAuthSessions(ctx context.Context, db *gorm.DB, now time.Time) error {
	return db.WithContext(contextOrBackground(ctx)).
		Where("status = ? AND expires_at <= ?", "complete", now).
		Delete(&OAuthSessionRecord{}).Error
}

// MergeOAuthSessionData merges an o auth session data.
func (r *Repository) MergeOAuthSessionData(ctx context.Context, state string, values map[string]any) error {
	// Resolve credential context before calling upstream OAuth services.
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	state = strings.TrimSpace(state)
	if state == "" {
		return fmt.Errorf("oauth state is required")
	}
	record, errRecord := r.GetOAuthSession(ctx, state)
	if errRecord != nil {
		return errRecord
	}
	if record == nil {
		return fmt.Errorf("oauth session not found")
	}
	if strings.TrimSpace(record.Status) != "" {
		return ErrOAuthSessionNotPending
	}
	data, errData := OAuthSessionData(record)
	if errData != nil {
		return errData
	}
	if data == nil {
		data = make(map[string]any, len(values))
	}
	for key, value := range values {
		key = strings.TrimSpace(key)
		if key == "" {
			continue
		}
		if value == nil {
			delete(data, key)
			continue
		}
		data[key] = value
	}
	rawData, errMarshal := json.Marshal(data)
	if errMarshal != nil {
		return errMarshal
	}
	record.Data = JSONB(rawData)
	record.UpdatedAt = time.Now().UTC()
	result := db.WithContext(contextOrBackground(ctx)).
		Model(record).
		Where("state = ? AND status = ?", state, "").
		Select("data", "updated_at").
		Updates(record)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return ErrOAuthSessionNotPending
	}
	return nil
}

// CompleteOAuthSession handles a complete o auth session.
func (r *Repository) CompleteOAuthSession(ctx context.Context, state string) error {
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	now := time.Now().UTC()
	return db.WithContext(contextOrBackground(ctx)).
		Model(&OAuthSessionRecord{}).
		Where("state = ? AND status != ?", strings.TrimSpace(state), "complete").
		Updates(map[string]any{
			"status":       "complete",
			"error":        "",
			"data":         nil,
			"updated_at":   now,
			"expires_at":   now.Add(oauthCompletedSessionTTL),
			"completed_at": &now,
		}).Error
}

// SetOAuthSessionError sets an o auth session error.
func (r *Repository) SetOAuthSessionError(ctx context.Context, state string, message string) error {
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	message = strings.TrimSpace(message)
	if message == "" {
		message = "Authentication failed"
	}
	now := time.Now().UTC()
	return db.WithContext(contextOrBackground(ctx)).
		Model(&OAuthSessionRecord{}).
		Where("state = ? AND status != ?", strings.TrimSpace(state), "complete").
		Updates(map[string]any{
			"status":     "error",
			"error":      message,
			"updated_at": now,
			"expires_at": now.Add(OAuthSessionTTL),
		}).Error
}
