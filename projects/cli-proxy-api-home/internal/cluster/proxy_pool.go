package cluster

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/proxyutil"
	"gorm.io/gorm"
)

const (
	ProxyPoolScopeGlobal = "global"

	ProxyPoolTestResultPassed   = "passed"
	ProxyPoolTestResultFailed   = "failed"
	ProxyPoolTestResultUntested = "untested"
)

type ProxyPoolRecord struct {
	ID             string         `gorm:"column:id;primaryKey"`
	Name           string         `gorm:"column:name;not null"`
	ProxyURL       string         `gorm:"column:proxy_url;not null"`
	Enabled        bool           `gorm:"column:enabled;not null;default:true"`
	Scope          string         `gorm:"column:scope;not null;default:global;index:idx_proxy_pool_scope_priority,priority:1"`
	Priority       int            `gorm:"column:priority;not null;default:0;index:idx_proxy_pool_scope_priority,priority:2"`
	LastTestedAt   *time.Time     `gorm:"column:last_tested_at"`
	LastTestResult string         `gorm:"column:last_test_result;not null;default:untested"`
	Note           string         `gorm:"column:note;type:text"`
	CreatedAt      time.Time      `gorm:"column:created_at;index:idx_proxy_pool_scope_priority,priority:3"`
	UpdatedAt      time.Time      `gorm:"column:updated_at"`
	DeletedAt      gorm.DeletedAt `gorm:"column:deleted_at;index"`
}

func (ProxyPoolRecord) TableName() string { return "proxy_pool" }

type ProxyPoolUpdate struct {
	Name     string
	ProxyURL string
	Enabled  *bool
	Scope    string
	Priority int
	Note     string
}

type ProxyPoolPatch struct {
	Name     *string
	ProxyURL *string
	Enabled  *bool
	Scope    *string
	Priority *int
	Note     *string
}

func (r *Repository) CreateProxyPoolItem(ctx context.Context, update ProxyPoolUpdate) (*ProxyPoolRecord, error) {
	normalized, errValidate := normalizeProxyPoolUpdate(update)
	if errValidate != nil {
		return nil, errValidate
	}
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}

	record := &ProxyPoolRecord{
		ID:             billingID("proxy"),
		Name:           normalized.Name,
		ProxyURL:       normalized.ProxyURL,
		Enabled:        proxyPoolEnabledOrDefault(normalized.Enabled),
		Scope:          normalized.Scope,
		Priority:       normalized.Priority,
		LastTestResult: ProxyPoolTestResultUntested,
		Note:           normalized.Note,
	}
	ctx = contextOrBackground(ctx)
	errTx := db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if errCreate := tx.Create(record).Error; errCreate != nil {
			return errCreate
		}
		if normalized.Enabled != nil && !*normalized.Enabled {
			if errUpdate := tx.Model(record).Update("enabled", false).Error; errUpdate != nil {
				return errUpdate
			}
			return tx.Where("id = ?", record.ID).First(record).Error
		}
		return nil
	})
	if errTx != nil {
		return nil, errTx
	}
	return record, nil
}

func (r *Repository) ListProxyPoolItems(ctx context.Context) ([]ProxyPoolRecord, error) {
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}
	var records []ProxyPoolRecord
	if errFind := db.WithContext(contextOrBackground(ctx)).
		Order("priority ASC, created_at ASC").
		Find(&records).Error; errFind != nil {
		return nil, errFind
	}
	return records, nil
}

func (r *Repository) GetProxyPoolItem(ctx context.Context, id string) (*ProxyPoolRecord, error) {
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}
	record := &ProxyPoolRecord{}
	if errFirst := db.WithContext(contextOrBackground(ctx)).Where("id = ?", strings.TrimSpace(id)).First(record).Error; errFirst != nil {
		return nil, errFirst
	}
	return record, nil
}

func (r *Repository) UpdateProxyPoolItem(ctx context.Context, id string, update ProxyPoolUpdate) (*ProxyPoolRecord, error) {
	normalized, errValidate := normalizeProxyPoolUpdate(update)
	if errValidate != nil {
		return nil, errValidate
	}
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}

	ctx = contextOrBackground(ctx)
	record := &ProxyPoolRecord{}
	errTx := db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if errFirst := tx.Where("id = ?", strings.TrimSpace(id)).First(record).Error; errFirst != nil {
			return errFirst
		}
		updates := map[string]any{
			"name":      normalized.Name,
			"proxy_url": normalized.ProxyURL,
			"enabled":   proxyPoolEnabledOrDefault(normalized.Enabled),
			"scope":     normalized.Scope,
			"priority":  normalized.Priority,
			"note":      normalized.Note,
		}
		if errUpdate := tx.Model(record).Updates(updates).Error; errUpdate != nil {
			return errUpdate
		}
		return tx.Where("id = ?", record.ID).First(record).Error
	})
	if errTx != nil {
		return nil, errTx
	}
	return record, nil
}

func (r *Repository) PatchProxyPoolItem(ctx context.Context, id string, patch ProxyPoolPatch) (*ProxyPoolRecord, error) {
	updates, errValidate := proxyPoolPatchUpdates(patch)
	if errValidate != nil {
		return nil, errValidate
	}
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}

	ctx = contextOrBackground(ctx)
	record := &ProxyPoolRecord{}
	errTx := db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if errFirst := tx.Where("id = ?", strings.TrimSpace(id)).First(record).Error; errFirst != nil {
			return errFirst
		}
		if len(updates) > 0 {
			if errUpdate := tx.Model(record).Updates(updates).Error; errUpdate != nil {
				return errUpdate
			}
		}
		return tx.Where("id = ?", record.ID).First(record).Error
	})
	if errTx != nil {
		return nil, errTx
	}
	return record, nil
}

func (r *Repository) DeleteProxyPoolItem(ctx context.Context, id string) error {
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	result := db.WithContext(contextOrBackground(ctx)).Where("id = ?", strings.TrimSpace(id)).Delete(&ProxyPoolRecord{})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}

func (r *Repository) MarkProxyPoolTestResult(ctx context.Context, id string, result string, testedAt time.Time) (*ProxyPoolRecord, error) {
	result = strings.ToLower(strings.TrimSpace(result))
	switch result {
	case ProxyPoolTestResultPassed, ProxyPoolTestResultFailed:
	default:
		return nil, fmt.Errorf("unsupported proxy pool test result %q", result)
	}
	if testedAt.IsZero() {
		testedAt = time.Now().UTC()
	} else {
		testedAt = testedAt.UTC()
	}

	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}
	ctx = contextOrBackground(ctx)
	record := &ProxyPoolRecord{}
	errTx := db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if errFirst := tx.Where("id = ?", strings.TrimSpace(id)).First(record).Error; errFirst != nil {
			return errFirst
		}
		if errUpdate := tx.Model(record).Updates(map[string]any{
			"last_tested_at":   testedAt,
			"last_test_result": result,
		}).Error; errUpdate != nil {
			return errUpdate
		}
		return tx.Where("id = ?", record.ID).First(record).Error
	})
	if errTx != nil {
		return nil, errTx
	}
	return record, nil
}

func normalizeProxyPoolUpdate(update ProxyPoolUpdate) (ProxyPoolUpdate, error) {
	normalized := ProxyPoolUpdate{
		Name:     strings.TrimSpace(update.Name),
		ProxyURL: strings.TrimSpace(update.ProxyURL),
		Enabled:  update.Enabled,
		Scope:    strings.ToLower(strings.TrimSpace(update.Scope)),
		Priority: update.Priority,
		Note:     strings.TrimSpace(update.Note),
	}
	if normalized.Name == "" {
		return normalized, fmt.Errorf("name is required")
	}
	if normalized.ProxyURL == "" {
		return normalized, fmt.Errorf("proxy_url is required")
	}
	if errValidate := validateProxyPoolURL(normalized.ProxyURL); errValidate != nil {
		return normalized, errValidate
	}
	if normalized.Scope == "" {
		normalized.Scope = ProxyPoolScopeGlobal
	}
	if normalized.Scope != ProxyPoolScopeGlobal {
		return normalized, fmt.Errorf("unsupported proxy pool scope %q", normalized.Scope)
	}
	return normalized, nil
}

func proxyPoolPatchUpdates(patch ProxyPoolPatch) (map[string]any, error) {
	updates := make(map[string]any)
	if patch.Name != nil {
		name := strings.TrimSpace(*patch.Name)
		if name == "" {
			return nil, fmt.Errorf("name is required")
		}
		updates["name"] = name
	}
	if patch.ProxyURL != nil {
		proxyURL := strings.TrimSpace(*patch.ProxyURL)
		if proxyURL == "" {
			return nil, fmt.Errorf("proxy_url is required")
		}
		if errValidate := validateProxyPoolURL(proxyURL); errValidate != nil {
			return nil, errValidate
		}
		updates["proxy_url"] = proxyURL
	}
	if patch.Enabled != nil {
		updates["enabled"] = *patch.Enabled
	}
	if patch.Scope != nil {
		scope := strings.ToLower(strings.TrimSpace(*patch.Scope))
		if scope != "" && scope != ProxyPoolScopeGlobal {
			return nil, fmt.Errorf("unsupported proxy pool scope %q", scope)
		}
		if scope != "" {
			updates["scope"] = scope
		}
	}
	if patch.Priority != nil {
		updates["priority"] = *patch.Priority
	}
	if patch.Note != nil {
		updates["note"] = strings.TrimSpace(*patch.Note)
	}
	return updates, nil
}

func validateProxyPoolURL(proxyURL string) error {
	setting, errParse := proxyutil.Parse(proxyURL)
	if errParse != nil {
		return errParse
	}
	if setting.Mode != proxyutil.ModeProxy || setting.URL == nil {
		return fmt.Errorf("proxy_url must include a supported proxy scheme and host")
	}
	return nil
}

func proxyPoolEnabledOrDefault(enabled *bool) bool {
	if enabled == nil {
		return true
	}
	return *enabled
}
