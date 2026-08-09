package management

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"gorm.io/gorm"
)

type apiKeyEntryBody struct {
	APIKey          *string `json:"api_key"`
	APIKeyDash      *string `json:"api-key"`
	Key             *string `json:"key"`
	Value           *string `json:"value"`
	UserID          *uint   `json:"user_id"`
	UserIDDash      *uint   `json:"user-id"`
	Channels        *[]uint `json:"channels"`
	ModelGroups     *[]uint `json:"model_groups"`
	ModelGroupsDash *[]uint `json:"model-groups"`
}

type apiKeyPatchBody struct {
	ID              *uint           `json:"id"`
	APIKeyID        *uint           `json:"api_key_id"`
	APIKeyIDDash    *uint           `json:"api-key-id"`
	Old             *string         `json:"old"`
	New             *string         `json:"new"`
	Index           *int            `json:"index"`
	Value           json.RawMessage `json:"value"`
	APIKey          *string         `json:"api_key"`
	APIKeyDash      *string         `json:"api-key"`
	Key             *string         `json:"key"`
	UserID          *uint           `json:"user_id"`
	UserIDDash      *uint           `json:"user-id"`
	Channels        *[]uint         `json:"channels"`
	ModelGroups     *[]uint         `json:"model_groups"`
	ModelGroupsDash *[]uint         `json:"model-groups"`
}

func apiKeyEntriesResponse(entries []cluster.APIKeyEntry) gin.H {
	keys := make([]string, 0, len(entries))
	items := make([]gin.H, 0, len(entries))
	for _, entry := range entries {
		key := strings.TrimSpace(entry.APIKey)
		if key == "" {
			continue
		}
		channels := append([]uint(nil), entry.Channels...)
		if channels == nil {
			channels = []uint{}
		}
		modelGroups := append([]uint(nil), entry.ModelGroups...)
		if modelGroups == nil {
			modelGroups = []uint{}
		}
		keys = append(keys, key)
		items = append(items, gin.H{
			"id":           entry.ID,
			"api_key_id":   entry.ID,
			"api-key":      key,
			"api_key":      key,
			"user-id":      optionalUserIDValue(entry.UserID),
			"user_id":      optionalUserIDValue(entry.UserID),
			"channels":     channels,
			"model_groups": modelGroups,
		})
	}
	return gin.H{
		"api-keys":        keys,
		"items":           items,
		"api_key_entries": items,
	}
}

func decodeAPIKeyEntryUpdates(data []byte) ([]cluster.APIKeyEntryUpdate, error) {
	if len(data) == 0 {
		return nil, fmt.Errorf("empty body")
	}
	if entries, errEntries := decodeAPIKeyEntryArray(data); errEntries == nil {
		return entries, nil
	}

	var wrapper map[string]json.RawMessage
	if errUnmarshal := json.Unmarshal(data, &wrapper); errUnmarshal != nil {
		return nil, errUnmarshal
	}
	for _, key := range []string{"items", "api-keys", "api_keys", "api_key_entries"} {
		raw := wrapper[key]
		if len(raw) == 0 {
			continue
		}
		return decodeAPIKeyEntryArray(raw)
	}
	return nil, fmt.Errorf("missing api key items")
}

func decodeAPIKeyEntryArray(data []byte) ([]cluster.APIKeyEntryUpdate, error) {
	var rawItems []json.RawMessage
	if errUnmarshal := json.Unmarshal(data, &rawItems); errUnmarshal != nil {
		return nil, errUnmarshal
	}
	entries := make([]cluster.APIKeyEntryUpdate, 0, len(rawItems))
	for _, raw := range rawItems {
		entry, errEntry := decodeAPIKeyEntry(raw)
		if errEntry != nil {
			return nil, errEntry
		}
		if strings.TrimSpace(entry.APIKey) == "" {
			continue
		}
		entries = append(entries, entry)
	}
	return entries, nil
}

func decodeAPIKeyEntry(data []byte) (cluster.APIKeyEntryUpdate, error) {
	var key string
	if errString := json.Unmarshal(data, &key); errString == nil {
		return cluster.APIKeyEntryUpdate{APIKey: strings.TrimSpace(key)}, nil
	}

	var body apiKeyEntryBody
	if errUnmarshal := json.Unmarshal(data, &body); errUnmarshal != nil {
		return cluster.APIKeyEntryUpdate{}, errUnmarshal
	}
	return cluster.APIKeyEntryUpdate{
		APIKey:      body.apiKey(),
		UserID:      body.userID(),
		Channels:    body.Channels,
		ModelGroups: body.modelGroups(),
	}, nil
}

func (b apiKeyEntryBody) apiKey() string {
	for _, value := range []*string{b.APIKey, b.APIKeyDash, b.Key, b.Value} {
		if value == nil {
			continue
		}
		if key := strings.TrimSpace(*value); key != "" {
			return key
		}
	}
	return ""
}

func (b apiKeyEntryBody) modelGroups() *[]uint {
	if b.ModelGroups != nil {
		return b.ModelGroups
	}
	return b.ModelGroupsDash
}

func (b apiKeyEntryBody) userID() *uint {
	if b.UserID != nil {
		return b.UserID
	}
	return b.UserIDDash
}

func (h *Handler) createAPIKeyEntry(c *gin.Context) {
	data, errData := c.GetRawData()
	if errData != nil {
		respondError(c, http.StatusBadRequest, "invalid_body", errData)
		return
	}
	entry, errEntry := decodeAPIKeyEntry(data)
	if errEntry != nil || strings.TrimSpace(entry.APIKey) == "" {
		respondError(c, http.StatusBadRequest, "invalid_body", errEntry)
		return
	}

	ctx, cancel := h.requestContext(c)
	defer cancel()
	record, errCreate := h.repo.CreateAPIKey(ctx, entry)
	if errCreate != nil {
		respondAPIKeyMutationError(c, errCreate)
		return
	}
	if errRefresh := h.refreshConfig(ctx); errRefresh != nil {
		respondError(c, http.StatusInternalServerError, "reload_failed", errRefresh)
		return
	}
	responseEntry, errResponseEntry := clusterAPIKeyEntryFromRecord(record)
	if errResponseEntry != nil {
		respondError(c, http.StatusInternalServerError, "api_key_load_failed", errResponseEntry)
		return
	}
	c.JSON(http.StatusCreated, gin.H{"api_key": apiKeyEntryToMap(responseEntry)})
}

func (h *Handler) patchAPIKeyEntries(c *gin.Context) error {
	var body apiKeyPatchBody
	if errBindJSON := c.ShouldBindJSON(&body); errBindJSON != nil {
		return fmt.Errorf("invalid body")
	}
	if body.id() != nil && (body.Index != nil || body.Old != nil) {
		return fmt.Errorf("invalid api key selector")
	}

	ctx, cancel := h.requestContext(c)
	defer cancel()

	selector := cluster.APIKeySelector{}
	update := cluster.APIKeyAdminUpdate{}
	appendIfMissing := false

	if body.Index != nil && len(body.Value) > 0 {
		if *body.Index < 0 {
			return fmt.Errorf("invalid index")
		}
		selector.Index = body.Index
		next, errEntry := decodeAPIKeyEntry(body.Value)
		if errEntry != nil {
			return fmt.Errorf("invalid value")
		}
		if strings.TrimSpace(next.APIKey) == "" {
			return fmt.Errorf("invalid value")
		}
		applyAPIKeyEntryUpdate(&update, next)
	} else if body.Old != nil && body.New != nil {
		oldKey := strings.TrimSpace(*body.Old)
		newKey := strings.TrimSpace(*body.New)
		if oldKey == "" || newKey == "" {
			return fmt.Errorf("missing fields")
		}
		selector.APIKey = oldKey
		update.APIKey = &newKey
		appendIfMissing = true
	} else {
		if id := body.id(); id != nil {
			if *id == 0 {
				return fmt.Errorf("invalid id")
			}
			selector.ID = *id
			selector.APIKey = body.apiKey()
		} else {
			selector.APIKey = body.apiKey()
		}
		if len(body.Value) > 0 {
			next, errEntry := decodeAPIKeyEntry(body.Value)
			if errEntry != nil {
				return fmt.Errorf("invalid value")
			}
			applyAPIKeyEntryUpdate(&update, next)
		}
		if body.New != nil {
			newKey := strings.TrimSpace(*body.New)
			if newKey == "" {
				return fmt.Errorf("invalid new value")
			}
			update.APIKey = &newKey
		}
		if userID := body.userID(); userID != nil {
			update.UserID = userID
		}
		if body.Channels != nil {
			update.Channels = body.Channels
		}
		if modelGroups := body.modelGroups(); modelGroups != nil {
			update.ModelGroups = modelGroups
		}
	}

	if update.APIKey == nil && update.UserID == nil && update.Channels == nil && update.ModelGroups == nil {
		return fmt.Errorf("missing fields")
	}
	if selector.ID == 0 && selector.Index == nil && strings.TrimSpace(selector.APIKey) == "" {
		return fmt.Errorf("missing api key selector")
	}

	record, errUpdate := h.repo.UpdateAPIKey(ctx, selector, update)
	if errUpdate != nil && appendIfMissing && errors.Is(errUpdate, gorm.ErrRecordNotFound) {
		record, errUpdate = h.repo.CreateAPIKey(ctx, cluster.APIKeyEntryUpdate{APIKey: *update.APIKey})
	}
	if errUpdate != nil {
		respondAPIKeyMutationError(c, errUpdate)
		return nil
	}
	if errRefresh := h.refreshConfig(ctx); errRefresh != nil {
		respondError(c, http.StatusInternalServerError, "reload_failed", errRefresh)
		return nil
	}
	responseEntry, errResponseEntry := clusterAPIKeyEntryFromRecord(record)
	if errResponseEntry != nil {
		respondError(c, http.StatusInternalServerError, "api_key_load_failed", errResponseEntry)
		return nil
	}
	c.JSON(http.StatusOK, gin.H{"api_key": apiKeyEntryToMap(responseEntry)})
	return nil
}

func (h *Handler) deleteAPIKeyEntry(c *gin.Context) error {
	selector := cluster.APIKeySelector{}
	if idRaw := firstNonEmptyQuery(c, "id", "api_key_id", "api-key-id"); idRaw != "" {
		id, errID := strconv.ParseUint(idRaw, 10, 64)
		if errID != nil || id == 0 {
			return fmt.Errorf("invalid id")
		}
		selector.ID = uint(id)
		selector.APIKey = firstNonEmptyQuery(c, "value", "api_key", "api-key", "key")
	}
	if idxRaw := c.Query("index"); idxRaw != "" {
		index, errIndex := strconv.Atoi(idxRaw)
		if errIndex != nil || index < 0 {
			return fmt.Errorf("invalid index")
		}
		selector.Index = &index
	}
	if selector.ID == 0 && selector.Index == nil {
		selector.APIKey = firstNonEmptyQuery(c, "value", "api_key", "api-key", "key")
	}
	if selector.ID == 0 && selector.Index == nil && strings.TrimSpace(selector.APIKey) == "" {
		return fmt.Errorf("missing id, index, or value")
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()

	if errDelete := h.repo.DeleteAPIKey(ctx, selector); errDelete != nil {
		respondAPIKeyMutationError(c, errDelete)
		return nil
	}
	if errRefresh := h.refreshConfig(ctx); errRefresh != nil {
		respondError(c, http.StatusInternalServerError, "reload_failed", errRefresh)
		return nil
	}
	respondOK(c)
	return nil
}

func applyAPIKeyEntryUpdate(update *cluster.APIKeyAdminUpdate, entry cluster.APIKeyEntryUpdate) {
	if update == nil {
		return
	}
	if key := strings.TrimSpace(entry.APIKey); key != "" {
		update.APIKey = &key
	}
	if entry.UserID != nil {
		update.UserID = entry.UserID
	}
	if entry.Channels != nil {
		update.Channels = entry.Channels
	}
	if entry.ModelGroups != nil {
		update.ModelGroups = entry.ModelGroups
	}
}

func respondAPIKeyMutationError(c *gin.Context, err error) {
	switch {
	case cluster.IsAPIKeyConflictError(err):
		respondError(c, http.StatusConflict, "api_key_exists", err)
	case errors.Is(err, cluster.ErrUserNotFound):
		respondError(c, http.StatusNotFound, "user_not_found", err)
	case errors.Is(err, gorm.ErrRecordNotFound):
		respondError(c, http.StatusNotFound, "api_key_not_found", err)
	case errors.Is(err, cluster.ErrAPIKeySelectorMismatch):
		respondError(c, http.StatusBadRequest, "invalid_api_key_selector", err)
	default:
		respondError(c, http.StatusInternalServerError, "write_failed", err)
	}
}

func (b apiKeyPatchBody) apiKey() string {
	for _, value := range []*string{b.APIKey, b.APIKeyDash, b.Key} {
		if value == nil {
			continue
		}
		if key := strings.TrimSpace(*value); key != "" {
			return key
		}
	}
	return ""
}

func clusterAPIKeyEntryFromRecord(record *cluster.APIKeyRecord) (cluster.APIKeyEntry, error) {
	return cluster.APIKeyEntryFromRecord(record)
}

func apiKeyEntryToMap(entry cluster.APIKeyEntry) gin.H {
	channels := append([]uint(nil), entry.Channels...)
	if channels == nil {
		channels = []uint{}
	}
	modelGroups := append([]uint(nil), entry.ModelGroups...)
	if modelGroups == nil {
		modelGroups = []uint{}
	}
	return gin.H{
		"id":           entry.ID,
		"api_key_id":   entry.ID,
		"api-key":      strings.TrimSpace(entry.APIKey),
		"api_key":      strings.TrimSpace(entry.APIKey),
		"user-id":      optionalUserIDValue(entry.UserID),
		"user_id":      optionalUserIDValue(entry.UserID),
		"channels":     channels,
		"model_groups": modelGroups,
	}
}

func (b apiKeyPatchBody) modelGroups() *[]uint {
	if b.ModelGroups != nil {
		return b.ModelGroups
	}
	return b.ModelGroupsDash
}

func (b apiKeyPatchBody) userID() *uint {
	if b.UserID != nil {
		return b.UserID
	}
	return b.UserIDDash
}

func (b apiKeyPatchBody) id() *uint {
	for _, value := range []*uint{b.ID, b.APIKeyID, b.APIKeyIDDash} {
		if value != nil {
			return value
		}
	}
	return nil
}

func normalizeAPIKeyEntryUserID(userID *uint) *uint {
	if userID == nil || *userID == 0 {
		return nil
	}
	value := *userID
	return &value
}

func optionalUserIDValue(userID *uint) any {
	userID = normalizeAPIKeyEntryUserID(userID)
	if userID == nil {
		return nil
	}
	return *userID
}
