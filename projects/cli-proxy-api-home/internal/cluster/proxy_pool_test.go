package cluster

import (
	"context"
	"errors"
	"testing"
	"time"

	"gorm.io/gorm"
)

func TestProxyPoolCRUDKeepsGlobalScopeOnly(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	repo, closeRepo := newBillingTestRepository(t, ctx)
	defer closeRepo()

	db, errDB := repo.database()
	if errDB != nil {
		t.Fatalf("database() error = %v", errDB)
	}
	if !db.Migrator().HasTable("proxy_pool") {
		t.Fatal("proxy_pool table was not migrated")
	}

	first, errCreateFirst := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "First proxy",
		ProxyURL: "http://127.0.0.1:18080",
		Enabled:  boolPtr(true),
		Priority: 20,
		Note:     "first note",
	})
	if errCreateFirst != nil {
		t.Fatalf("CreateProxyPoolItem(first) error = %v", errCreateFirst)
	}
	if first.ID == "" {
		t.Fatal("CreateProxyPoolItem(first) ID is empty")
	}
	if first.Scope != ProxyPoolScopeGlobal {
		t.Fatalf("first scope = %q, want global", first.Scope)
	}
	if first.LastTestResult != ProxyPoolTestResultUntested {
		t.Fatalf("first last_test_result = %q, want untested", first.LastTestResult)
	}

	second, errCreateSecond := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "Second proxy",
		ProxyURL: "socks5h://127.0.0.1:19090",
		Enabled:  boolPtr(true),
		Scope:    ProxyPoolScopeGlobal,
		Priority: 10,
	})
	if errCreateSecond != nil {
		t.Fatalf("CreateProxyPoolItem(second) error = %v", errCreateSecond)
	}
	if second.Scope != ProxyPoolScopeGlobal {
		t.Fatalf("second scope = %q, want global", second.Scope)
	}

	if _, errCreateScoped := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "Team proxy",
		ProxyURL: "http://127.0.0.1:18081",
		Scope:    "team",
	}); errCreateScoped == nil {
		t.Fatal("CreateProxyPoolItem(non-global scope) error = nil, want validation error")
	}

	updated, errUpdate := repo.UpdateProxyPoolItem(ctx, first.ID, ProxyPoolUpdate{
		Name:     "First proxy updated",
		ProxyURL: "https://127.0.0.1:18082",
		Enabled:  boolPtr(false),
		Priority: 5,
		Note:     "updated note",
	})
	if errUpdate != nil {
		t.Fatalf("UpdateProxyPoolItem() error = %v", errUpdate)
	}
	if updated.Name != "First proxy updated" || updated.Priority != 5 || updated.Enabled || updated.Note != "updated note" {
		t.Fatalf("updated record = %#v, want changed name/priority/enabled/note", updated)
	}

	items, errList := repo.ListProxyPoolItems(ctx)
	if errList != nil {
		t.Fatalf("ListProxyPoolItems() error = %v", errList)
	}
	if len(items) != 2 {
		t.Fatalf("item count = %d, want 2", len(items))
	}
	if items[0].ID != first.ID || items[1].ID != second.ID {
		t.Fatalf("list order IDs = %q, %q; want first, second", items[0].ID, items[1].ID)
	}

	if errDelete := repo.DeleteProxyPoolItem(ctx, first.ID); errDelete != nil {
		t.Fatalf("DeleteProxyPoolItem() error = %v", errDelete)
	}
	if _, errGet := repo.GetProxyPoolItem(ctx, first.ID); !errors.Is(errGet, gorm.ErrRecordNotFound) {
		t.Fatalf("GetProxyPoolItem(deleted) error = %v, want record not found", errGet)
	}
	items, errList = repo.ListProxyPoolItems(ctx)
	if errList != nil {
		t.Fatalf("ListProxyPoolItems(after delete) error = %v", errList)
	}
	if len(items) != 1 || items[0].ID != second.ID {
		t.Fatalf("items after delete = %#v, want only second item", items)
	}
}

func TestProxyPoolValidationRejectsInvalidInput(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	repo, closeRepo := newBillingTestRepository(t, ctx)
	defer closeRepo()

	tests := []struct {
		name   string
		update ProxyPoolUpdate
	}{
		{
			name: "missing name",
			update: ProxyPoolUpdate{
				ProxyURL: "http://127.0.0.1:18080",
			},
		},
		{
			name: "missing host",
			update: ProxyPoolUpdate{
				Name:     "Missing host",
				ProxyURL: "http://",
			},
		},
		{
			name: "unsupported scheme",
			update: ProxyPoolUpdate{
				Name:     "FTP proxy",
				ProxyURL: "ftp://127.0.0.1:21",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if _, errCreate := repo.CreateProxyPoolItem(ctx, tt.update); errCreate == nil {
				t.Fatal("CreateProxyPoolItem() error = nil, want validation error")
			}
		})
	}

	if _, errCreate := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "SOCKS5H proxy",
		ProxyURL: "socks5h://127.0.0.1:19090",
	}); errCreate != nil {
		t.Fatalf("CreateProxyPoolItem(socks5h) error = %v", errCreate)
	}
}

func TestProxyPoolCreateDefaultsEnabled(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	repo, closeRepo := newBillingTestRepository(t, ctx)
	defer closeRepo()

	record, errCreate := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "Default enabled proxy",
		ProxyURL: "http://127.0.0.1:18080",
	})
	if errCreate != nil {
		t.Fatalf("CreateProxyPoolItem() error = %v", errCreate)
	}
	if !record.Enabled {
		t.Fatal("CreateProxyPoolItem() Enabled = false, want true by default")
	}

	stored, errGet := repo.GetProxyPoolItem(ctx, record.ID)
	if errGet != nil {
		t.Fatalf("GetProxyPoolItem() error = %v", errGet)
	}
	if !stored.Enabled {
		t.Fatal("stored Enabled = false, want true by default")
	}

	disabled, errCreateDisabled := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "Explicit disabled proxy",
		ProxyURL: "http://127.0.0.1:18081",
		Enabled:  boolPtr(false),
	})
	if errCreateDisabled != nil {
		t.Fatalf("CreateProxyPoolItem(disabled) error = %v", errCreateDisabled)
	}
	if disabled.Enabled {
		t.Fatal("CreateProxyPoolItem(disabled) Enabled = true, want false")
	}
}

func TestProxyPoolPatchPreservesUnspecifiedFields(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	repo, closeRepo := newBillingTestRepository(t, ctx)
	defer closeRepo()

	record, errCreate := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "Patch proxy",
		ProxyURL: "http://127.0.0.1:18080",
		Enabled:  boolPtr(true),
		Scope:    ProxyPoolScopeGlobal,
		Priority: 30,
		Note:     "keep note",
	})
	if errCreate != nil {
		t.Fatalf("CreateProxyPoolItem() error = %v", errCreate)
	}

	enabled := false
	updated, errPatch := repo.PatchProxyPoolItem(ctx, record.ID, ProxyPoolPatch{Enabled: &enabled})
	if errPatch != nil {
		t.Fatalf("PatchProxyPoolItem() error = %v", errPatch)
	}
	if updated.Enabled {
		t.Fatal("patched Enabled = true, want false")
	}
	if updated.Name != record.Name || updated.ProxyURL != record.ProxyURL || updated.Scope != record.Scope || updated.Priority != record.Priority || updated.Note != record.Note {
		t.Fatalf("patched record = %#v, want unspecified fields preserved from %#v", updated, record)
	}
}

func TestProxyPoolMarkTestResult(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	repo, closeRepo := newBillingTestRepository(t, ctx)
	defer closeRepo()

	record, errCreate := repo.CreateProxyPoolItem(ctx, ProxyPoolUpdate{
		Name:     "Proxy under test",
		ProxyURL: "http://127.0.0.1:18080",
	})
	if errCreate != nil {
		t.Fatalf("CreateProxyPoolItem() error = %v", errCreate)
	}

	testedAt := time.Date(2026, time.June, 10, 1, 2, 3, 0, time.UTC)
	updated, errMark := repo.MarkProxyPoolTestResult(ctx, record.ID, ProxyPoolTestResultPassed, testedAt)
	if errMark != nil {
		t.Fatalf("MarkProxyPoolTestResult() error = %v", errMark)
	}
	if updated.LastTestedAt == nil || !updated.LastTestedAt.Equal(testedAt) {
		t.Fatalf("LastTestedAt = %v, want %s", updated.LastTestedAt, testedAt.Format(time.RFC3339))
	}
	if updated.LastTestResult != ProxyPoolTestResultPassed {
		t.Fatalf("LastTestResult = %q, want passed", updated.LastTestResult)
	}

	if _, errMarkInvalid := repo.MarkProxyPoolTestResult(ctx, record.ID, ProxyPoolTestResultUntested, testedAt); errMarkInvalid == nil {
		t.Fatal("MarkProxyPoolTestResult(untested) error = nil, want validation error")
	}
}

func boolPtr(value bool) *bool {
	return &value
}
