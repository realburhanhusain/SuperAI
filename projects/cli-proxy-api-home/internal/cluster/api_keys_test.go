package cluster

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func TestUpdateAPIKeyForUserRejectsDuplicateRename(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	db, errOpenSQLite := OpenSQLite(ctx, filepath.Join(t.TempDir(), "home.db"))
	if errOpenSQLite != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpenSQLite)
	}
	sqlDB, errDB := db.DB()
	if errDB != nil {
		t.Fatalf("get sqlite db: %v", errDB)
	}
	defer func() {
		if errClose := sqlDB.Close(); errClose != nil {
			t.Errorf("close sqlite db: %v", errClose)
		}
	}()
	if errMigrate := AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}

	repo := NewRepository(db)
	firstUsername := "first-user"
	secondUsername := "second-user"
	firstUser, errCreateFirstUser := repo.CreateUser(ctx, UserUpdate{Username: &firstUsername})
	if errCreateFirstUser != nil {
		t.Fatalf("CreateUser(first) error = %v", errCreateFirstUser)
	}
	secondUser, errCreateSecondUser := repo.CreateUser(ctx, UserUpdate{Username: &secondUsername})
	if errCreateSecondUser != nil {
		t.Fatalf("CreateUser(second) error = %v", errCreateSecondUser)
	}

	firstKey := "first-client-key"
	secondKey := "second-client-key"
	if _, errCreateFirstKey := repo.CreateAPIKeyForUser(ctx, firstUser.ID, APIKeyUserUpdate{APIKey: &firstKey}); errCreateFirstKey != nil {
		t.Fatalf("CreateAPIKeyForUser(first) error = %v", errCreateFirstKey)
	}
	if _, errCreateSecondKey := repo.CreateAPIKeyForUser(ctx, secondUser.ID, APIKeyUserUpdate{APIKey: &secondKey}); errCreateSecondKey != nil {
		t.Fatalf("CreateAPIKeyForUser(second) error = %v", errCreateSecondKey)
	}

	_, errRenameActive := repo.UpdateAPIKeyForUser(ctx, firstUser.ID, 0, firstKey, APIKeyUserUpdate{APIKey: &secondKey})
	if !errors.Is(errRenameActive, ErrAPIKeyExists) {
		t.Fatalf("UpdateAPIKeyForUser(active duplicate) error = %v, want ErrAPIKeyExists", errRenameActive)
	}

	if errDeleteSecondKey := repo.DeleteAPIKeyForUser(ctx, secondUser.ID, 0, secondKey); errDeleteSecondKey != nil {
		t.Fatalf("DeleteAPIKeyForUser(second) error = %v", errDeleteSecondKey)
	}
	_, errRenameDeleted := repo.UpdateAPIKeyForUser(ctx, firstUser.ID, 0, firstKey, APIKeyUserUpdate{APIKey: &secondKey})
	if !errors.Is(errRenameDeleted, ErrAPIKeyExists) {
		t.Fatalf("UpdateAPIKeyForUser(deleted duplicate) error = %v, want ErrAPIKeyExists", errRenameDeleted)
	}

	records, errList := repo.ListAPIKeyRecordsForUser(ctx, firstUser.ID)
	if errList != nil {
		t.Fatalf("ListAPIKeyRecordsForUser() error = %v", errList)
	}
	if len(records) != 1 || records[0].APIKey != firstKey {
		t.Fatalf("first user API keys = %#v, want only %q", records, firstKey)
	}
}
