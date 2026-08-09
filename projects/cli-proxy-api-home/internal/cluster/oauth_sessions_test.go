package cluster

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"

	"gorm.io/gorm"
)

func TestCompleteOAuthSessionCreatesShortLivedTombstone(t *testing.T) {
	repo, ctx := newOAuthSessionTestRepository(t)
	record, errRecord := NewOAuthSessionRecord("codex", "completed-state", map[string]any{"code_verifier": "secret"}, time.Now().UTC())
	if errRecord != nil {
		t.Fatalf("NewOAuthSessionRecord() error = %v", errRecord)
	}
	if errUpsert := repo.UpsertOAuthSession(ctx, record); errUpsert != nil {
		t.Fatalf("UpsertOAuthSession() error = %v", errUpsert)
	}

	completedAt := time.Now().UTC()
	if errComplete := repo.CompleteOAuthSession(ctx, record.State); errComplete != nil {
		t.Fatalf("CompleteOAuthSession() error = %v", errComplete)
	}

	completed, errGet := repo.GetOAuthSession(ctx, record.State)
	if errGet != nil {
		t.Fatalf("GetOAuthSession() error = %v", errGet)
	}
	if completed == nil || completed.Status != "complete" || completed.CompletedAt == nil {
		t.Fatalf("completed session = %+v, want completed tombstone", completed)
	}
	if len(completed.Data) != 0 {
		t.Fatalf("completed session data = %q, want cleared", string(completed.Data))
	}
	wantExpiry := completedAt.Add(time.Minute)
	if completed.ExpiresAt.Before(wantExpiry.Add(-time.Second)) || completed.ExpiresAt.After(wantExpiry.Add(time.Second)) {
		t.Fatalf("completed expiry = %s, want about %s", completed.ExpiresAt, wantExpiry)
	}
}

func TestCompleteOAuthSessionDoesNotExtendTombstone(t *testing.T) {
	repo, ctx := newOAuthSessionTestRepository(t)
	record, errRecord := NewOAuthSessionRecord("codex", "idempotent-state", nil, time.Now().UTC())
	if errRecord != nil {
		t.Fatalf("NewOAuthSessionRecord() error = %v", errRecord)
	}
	if errUpsert := repo.UpsertOAuthSession(ctx, record); errUpsert != nil {
		t.Fatalf("UpsertOAuthSession() error = %v", errUpsert)
	}
	if errComplete := repo.CompleteOAuthSession(ctx, record.State); errComplete != nil {
		t.Fatalf("CompleteOAuthSession() error = %v", errComplete)
	}

	stableCompletedAt := time.Now().UTC().Add(-10 * time.Second).Truncate(time.Millisecond)
	stableUpdatedAt := stableCompletedAt
	stableExpiresAt := time.Now().UTC().Add(30 * time.Second).Truncate(time.Millisecond)
	if errUpdate := repo.db.Model(&OAuthSessionRecord{}).
		Where("state = ?", record.State).
		Updates(map[string]any{
			"completed_at": stableCompletedAt,
			"updated_at":   stableUpdatedAt,
			"expires_at":   stableExpiresAt,
		}).Error; errUpdate != nil {
		t.Fatalf("set stable tombstone timestamps: %v", errUpdate)
	}

	if errComplete := repo.CompleteOAuthSession(ctx, record.State); errComplete != nil {
		t.Fatalf("repeated CompleteOAuthSession() error = %v", errComplete)
	}

	completed := &OAuthSessionRecord{}
	if errFirst := repo.db.Where("state = ?", record.State).First(completed).Error; errFirst != nil {
		t.Fatalf("load completed session: %v", errFirst)
	}
	if completed.CompletedAt == nil || !completed.CompletedAt.Equal(stableCompletedAt) {
		t.Fatalf("completed_at = %v, want %s", completed.CompletedAt, stableCompletedAt)
	}
	if !completed.UpdatedAt.Equal(stableUpdatedAt) {
		t.Fatalf("updated_at = %s, want %s", completed.UpdatedAt, stableUpdatedAt)
	}
	if !completed.ExpiresAt.Equal(stableExpiresAt) {
		t.Fatalf("expires_at = %s, want %s", completed.ExpiresAt, stableExpiresAt)
	}
}

func TestUpsertOAuthSessionRemovesAllExpiredCompletedTombstones(t *testing.T) {
	repo, ctx := newOAuthSessionTestRepository(t)
	now := time.Now().UTC()
	completedAt := now.Add(-2 * time.Minute)
	expired := &OAuthSessionRecord{
		State:       "expired-completed-state",
		Provider:    "codex",
		Status:      "complete",
		CreatedAt:   completedAt,
		UpdatedAt:   completedAt,
		ExpiresAt:   now.Add(-time.Minute),
		CompletedAt: &completedAt,
	}
	if errUpsert := repo.UpsertOAuthSession(ctx, expired); errUpsert != nil {
		t.Fatalf("UpsertOAuthSession() error = %v", errUpsert)
	}
	active, errActive := NewOAuthSessionRecord("codex", "active-state", nil, now)
	if errActive != nil {
		t.Fatalf("NewOAuthSessionRecord() error = %v", errActive)
	}
	if errUpsert := repo.UpsertOAuthSession(ctx, active); errUpsert != nil {
		t.Fatalf("UpsertOAuthSession() active error = %v", errUpsert)
	}

	got, errGet := repo.GetOAuthSession(ctx, active.State)
	if errGet != nil {
		t.Fatalf("GetOAuthSession() error = %v", errGet)
	}
	if got == nil || got.State != active.State {
		t.Fatalf("GetOAuthSession() = %+v, want active session", got)
	}

	var count int64
	if errCount := repo.db.Model(&OAuthSessionRecord{}).Where("state = ?", expired.State).Count(&count).Error; errCount != nil {
		t.Fatalf("count expired tombstone: %v", errCount)
	}
	if count != 0 {
		t.Fatalf("expired tombstone count = %d, want 0", count)
	}
}

func TestMergeOAuthSessionDataDoesNotOverwriteConcurrentCompletion(t *testing.T) {
	repo, ctx := newOAuthSessionTestRepository(t)
	record, errRecord := NewOAuthSessionRecord("codex", "concurrent-completion-state", map[string]any{"code_verifier": "secret"}, time.Now().UTC())
	if errRecord != nil {
		t.Fatalf("NewOAuthSessionRecord() error = %v", errRecord)
	}
	if errUpsert := repo.UpsertOAuthSession(ctx, record); errUpsert != nil {
		t.Fatalf("UpsertOAuthSession() error = %v", errUpsert)
	}
	sqlDB, errDB := repo.db.DB()
	if errDB != nil {
		t.Fatalf("DB() error = %v", errDB)
	}
	sqlDB.SetMaxOpenConns(2)
	sqlDB.SetMaxIdleConns(2)

	mergeReachedUpdate := make(chan struct{})
	releaseMerge := make(chan struct{})
	if errCallback := repo.db.Callback().Update().Before("gorm:update").Register("test:block_oauth_merge", func(tx *gorm.DB) {
		session, ok := tx.Statement.Dest.(*OAuthSessionRecord)
		if !ok || session.State != record.State || session.Status != "" {
			return
		}
		mergeReachedUpdate <- struct{}{}
		<-releaseMerge
	}); errCallback != nil {
		t.Fatalf("register update callback: %v", errCallback)
	}

	mergeDone := make(chan error, 1)
	go func() {
		mergeDone <- repo.MergeOAuthSessionData(context.Background(), record.State, map[string]any{"callback_received_at": "late"})
	}()

	<-mergeReachedUpdate
	if errComplete := repo.CompleteOAuthSession(ctx, record.State); errComplete != nil {
		t.Fatalf("CompleteOAuthSession() error = %v", errComplete)
	}
	close(releaseMerge)
	if errMerge := <-mergeDone; !errors.Is(errMerge, ErrOAuthSessionNotPending) {
		t.Fatalf("MergeOAuthSessionData() error = %v, want ErrOAuthSessionNotPending", errMerge)
	}

	completed, errGet := repo.GetOAuthSession(ctx, record.State)
	if errGet != nil {
		t.Fatalf("GetOAuthSession() error = %v", errGet)
	}
	if completed == nil || completed.Status != "complete" || completed.CompletedAt == nil || len(completed.Data) != 0 {
		t.Fatalf("completed session = %+v, want unchanged completed tombstone", completed)
	}
}

func TestSetOAuthSessionErrorDoesNotOverwriteCompletedSession(t *testing.T) {
	repo, ctx := newOAuthSessionTestRepository(t)
	record, errRecord := NewOAuthSessionRecord("codex", "completed-error-state", nil, time.Now().UTC())
	if errRecord != nil {
		t.Fatalf("NewOAuthSessionRecord() error = %v", errRecord)
	}
	if errUpsert := repo.UpsertOAuthSession(ctx, record); errUpsert != nil {
		t.Fatalf("UpsertOAuthSession() error = %v", errUpsert)
	}
	if errComplete := repo.CompleteOAuthSession(ctx, record.State); errComplete != nil {
		t.Fatalf("CompleteOAuthSession() error = %v", errComplete)
	}
	if errSet := repo.SetOAuthSessionError(ctx, record.State, "late failure"); errSet != nil {
		t.Fatalf("SetOAuthSessionError() error = %v", errSet)
	}

	completed, errGet := repo.GetOAuthSession(ctx, record.State)
	if errGet != nil {
		t.Fatalf("GetOAuthSession() error = %v", errGet)
	}
	if completed == nil || completed.Status != "complete" || completed.Error != "" {
		t.Fatalf("completed session = %+v, want unchanged completion", completed)
	}
}

func newOAuthSessionTestRepository(t *testing.T) (*Repository, context.Context) {
	t.Helper()

	ctx := context.Background()
	db, errOpen := OpenSQLite(ctx, filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpen)
	}
	sqlDB, errDB := db.DB()
	if errDB != nil {
		t.Fatalf("DB() error = %v", errDB)
	}
	t.Cleanup(func() {
		if errClose := sqlDB.Close(); errClose != nil {
			t.Errorf("close sqlite db: %v", errClose)
		}
	})
	if errMigrate := AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	return NewRepository(db), ctx
}
