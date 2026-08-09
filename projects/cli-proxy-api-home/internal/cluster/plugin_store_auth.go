package cluster

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"strconv"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const (
	pluginStoreAuthEventScope = "plugin-store-auth"
	pluginStoreAuthKeyID      = 1
	pluginStoreAuthKeyVersion = 1
	pluginStoreAuthKeySize    = 32
)

// ErrPluginStoreAuthConflict indicates an optimistic update conflict.
var ErrPluginStoreAuthConflict = errors.New("plugin store auth update conflict")

type PluginStoreAuthSealFunc func(id uint) ([]byte, int, error)

func (r *Repository) EnsurePluginStoreAuthKey(ctx context.Context) ([]byte, int, error) {
	db, errDB := r.database()
	if errDB != nil {
		return nil, 0, errDB
	}
	candidate := make([]byte, pluginStoreAuthKeySize)
	if _, errRandom := rand.Read(candidate); errRandom != nil {
		return nil, 0, fmt.Errorf("generate plugin store auth key: %w", errRandom)
	}
	defer clearBytes(candidate)
	record := PluginStoreAuthKeyRecord{
		ID:         pluginStoreAuthKeyID,
		Key:        candidate,
		KeyVersion: pluginStoreAuthKeyVersion,
	}
	if errCreate := db.WithContext(contextOrBackground(ctx)).Clauses(clause.OnConflict{DoNothing: true}).Create(&record).Error; errCreate != nil {
		return nil, 0, errCreate
	}
	stored := PluginStoreAuthKeyRecord{}
	if errFirst := db.WithContext(contextOrBackground(ctx)).First(&stored, pluginStoreAuthKeyID).Error; errFirst != nil {
		return nil, 0, errFirst
	}
	if len(stored.Key) != pluginStoreAuthKeySize || stored.KeyVersion <= 0 {
		clearBytes(stored.Key)
		return nil, 0, fmt.Errorf("plugin store auth key is invalid")
	}
	key := append([]byte(nil), stored.Key...)
	clearBytes(stored.Key)
	return key, stored.KeyVersion, nil
}

func (r *Repository) CreatePluginStoreAuth(ctx context.Context, record *PluginStoreAuthRecord, seal PluginStoreAuthSealFunc) error {
	if record == nil {
		return fmt.Errorf("plugin store auth record is nil")
	}
	if seal == nil {
		return fmt.Errorf("plugin store auth seal function is nil")
	}
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	enabled := record.Enabled
	record.ID = 0
	record.Version = 1
	return db.WithContext(contextOrBackground(ctx)).Transaction(func(tx *gorm.DB) error {
		record.EncryptedCredentials = nil
		record.KeyVersion = 0
		if errCreate := tx.Create(record).Error; errCreate != nil {
			return errCreate
		}
		encrypted, keyVersion, errSeal := seal(record.ID)
		if errSeal != nil {
			return errSeal
		}
		defer clearBytes(encrypted)
		if errUpdate := tx.Model(record).Updates(map[string]any{
			"encrypted_credentials": encrypted,
			"enabled":               enabled,
			"key_version":           keyVersion,
		}).Error; errUpdate != nil {
			return errUpdate
		}
		record.EncryptedCredentials = append(record.EncryptedCredentials[:0], encrypted...)
		record.Enabled = enabled
		record.KeyVersion = keyVersion
		return appendEvent(tx, pluginStoreAuthEventScope, "create", strconv.FormatUint(uint64(record.ID), 10), record.Version)
	})
}

func (r *Repository) ListPluginStoreAuth(ctx context.Context) ([]PluginStoreAuthRecord, error) {
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}
	var records []PluginStoreAuthRecord
	if errFind := db.WithContext(contextOrBackground(ctx)).Order("id").Find(&records).Error; errFind != nil {
		return nil, errFind
	}
	return records, nil
}

func (r *Repository) GetPluginStoreAuth(ctx context.Context, id uint) (*PluginStoreAuthRecord, error) {
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}
	record := &PluginStoreAuthRecord{}
	if errFirst := db.WithContext(contextOrBackground(ctx)).First(record, id).Error; errFirst != nil {
		return nil, errFirst
	}
	return record, nil
}

func (r *Repository) UpdatePluginStoreAuth(ctx context.Context, record *PluginStoreAuthRecord) error {
	if record == nil || record.ID == 0 || record.Version <= 0 {
		return fmt.Errorf("plugin store auth record identity is invalid")
	}
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	return db.WithContext(contextOrBackground(ctx)).Transaction(func(tx *gorm.DB) error {
		nextVersion := record.Version + 1
		updates := map[string]any{
			"name": record.Name, "match": record.Match, "apply_to": record.ApplyTo,
			"auth_type": record.AuthType, "header_name": record.HeaderName,
			"encrypted_credentials": record.EncryptedCredentials, "key_version": record.KeyVersion,
			"enabled": record.Enabled, "version": nextVersion,
		}
		result := tx.Model(&PluginStoreAuthRecord{}).Where("id = ? AND version = ?", record.ID, record.Version).Updates(updates)
		if result.Error != nil {
			return result.Error
		}
		if result.RowsAffected != 1 {
			return ErrPluginStoreAuthConflict
		}
		record.Version = nextVersion
		return appendEvent(tx, pluginStoreAuthEventScope, "update", strconv.FormatUint(uint64(record.ID), 10), nextVersion)
	})
}

func (r *Repository) DeletePluginStoreAuth(ctx context.Context, id uint) error {
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	return db.WithContext(contextOrBackground(ctx)).Transaction(func(tx *gorm.DB) error {
		record := PluginStoreAuthRecord{}
		if errFirst := tx.First(&record, id).Error; errFirst != nil {
			return errFirst
		}
		defer clearBytes(record.EncryptedCredentials)
		if errDelete := tx.Delete(&PluginStoreAuthRecord{}, id).Error; errDelete != nil {
			return errDelete
		}
		return appendEvent(tx, pluginStoreAuthEventScope, "delete", strconv.FormatUint(uint64(id), 10), record.Version+1)
	})
}

func (r *Repository) PluginStoreAuthRevision(ctx context.Context) (int64, error) {
	db, errDB := r.database()
	if errDB != nil {
		return 0, errDB
	}
	var revision int64
	if errScan := db.WithContext(contextOrBackground(ctx)).Model(&ClusterEventRecord{}).
		Where("scope = ?", pluginStoreAuthEventScope).
		Select("COALESCE(MAX(id), 0)").Scan(&revision).Error; errScan != nil {
		return 0, errScan
	}
	return revision, nil
}

func clearBytes(value []byte) {
	for index := range value {
		value[index] = 0
	}
}
