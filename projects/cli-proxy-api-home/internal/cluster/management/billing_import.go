package management

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
)

const (
	modelsDevCatalogURL                  = "https://models.dev/api.json"
	modelsDevDefaultCacheReadInputRatio  = 0.1
	modelsDevDefaultCacheWriteInputRatio = 1.25
	billingImportMaxRequestBodySize      = 4 << 20
)

func (h *Handler) PreviewBillingModelPriceImport(c *gin.Context) {
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, billingImportMaxRequestBodySize)
	var body cluster.BillingModelPriceImportPreviewInput
	if errBind := c.ShouldBindJSON(&body); errBind != nil {
		respondError(c, http.StatusBadRequest, "invalid_body", errBind)
		return
	}
	if errValidate := cluster.ValidateBillingModelPriceImportPreviewInput(body); errValidate != nil {
		respondError(c, http.StatusUnprocessableEntity, "invalid_import_preview", errValidate)
		return
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()
	catalog, errCatalog := h.fetchBillingModelPriceImportCatalog(ctx)
	if errCatalog != nil {
		respondError(c, http.StatusBadGateway, "models_dev_fetch_failed", errCatalog)
		return
	}
	preview, errPreview := h.repo.CreateBillingModelPriceImportPreview(ctx, body, catalog)
	if errPreview != nil {
		respondError(c, http.StatusInternalServerError, "billing_import_preview_failed", errPreview)
		return
	}
	c.JSON(http.StatusOK, preview)
}

func (h *Handler) ApplyBillingModelPriceImport(c *gin.Context) {
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, billingImportMaxRequestBodySize)
	var body cluster.BillingModelPriceImportApplyInput
	if errBind := c.ShouldBindJSON(&body); errBind != nil {
		respondError(c, http.StatusBadRequest, "invalid_body", errBind)
		return
	}
	headerKey := strings.TrimSpace(c.GetHeader("Idempotency-Key"))
	if body.IdempotencyKey == "" {
		body.IdempotencyKey = headerKey
	} else if headerKey != "" && body.IdempotencyKey != headerKey {
		respondError(c, http.StatusUnprocessableEntity, "idempotency_key_mismatch", fmt.Errorf("Idempotency-Key header does not match request body"))
		return
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()
	operation, errApply := h.repo.ApplyBillingModelPriceImport(ctx, body)
	if errApply != nil {
		switch {
		case errors.Is(errApply, cluster.ErrBillingImportPreviewNotFound):
			respondError(c, http.StatusNotFound, "import_preview_not_found", errApply)
		case errors.Is(errApply, cluster.ErrBillingImportPreviewExpired):
			respondError(c, http.StatusGone, "import_preview_expired", errApply)
		case errors.Is(errApply, cluster.ErrBillingImportPreviewStale):
			respondError(c, http.StatusPreconditionFailed, "import_preview_stale", errApply)
		case errors.Is(errApply, cluster.ErrBillingImportRuleConflict):
			respondError(c, http.StatusConflict, "model_price_revision_conflict", errApply)
		case errors.Is(errApply, cluster.ErrBillingImportInvalidSelection), errors.Is(errApply, cluster.ErrBillingImportOverwriteRequired), errors.Is(errApply, cluster.ErrBillingImportIdempotencyConflict):
			respondError(c, http.StatusUnprocessableEntity, "invalid_import_apply", errApply)
		default:
			respondError(c, http.StatusInternalServerError, "billing_import_apply_failed", errApply)
		}
		return
	}
	c.JSON(http.StatusOK, operation)
}

func (h *Handler) GetBillingModelPriceImportOperation(c *gin.Context) {
	ctx, cancel := h.requestContext(c)
	defer cancel()
	operation, errOperation := h.repo.GetBillingModelPriceImportOperation(ctx, c.Param("id"))
	if errOperation != nil {
		if errors.Is(errOperation, cluster.ErrBillingImportOperationNotFound) {
			respondError(c, http.StatusNotFound, "import_operation_not_found", errOperation)
			return
		}
		respondError(c, http.StatusInternalServerError, "billing_import_operation_load_failed", errOperation)
		return
	}
	c.JSON(http.StatusOK, operation)
}

func (h *Handler) GetBillingTierDiagnostics(c *gin.Context) {
	ctx, cancel := h.requestContext(c)
	defer cancel()
	diagnostics, errDiagnostics := h.repo.GetBillingTierDiagnostics(ctx)
	if errDiagnostics != nil {
		respondError(c, http.StatusInternalServerError, "billing_tier_diagnostics_load_failed", errDiagnostics)
		return
	}
	c.JSON(http.StatusOK, diagnostics)
}

func (h *Handler) fetchBillingModelPriceImportCatalog(ctx context.Context) (cluster.BillingModelPriceImportCatalog, error) {
	client := h.modelsDevHTTPClient
	if client == nil {
		client = &http.Client{Timeout: 8 * time.Second}
	}
	req, errRequest := http.NewRequestWithContext(ctx, http.MethodGet, modelsDevCatalogURL, nil)
	if errRequest != nil {
		return cluster.BillingModelPriceImportCatalog{}, errRequest
	}
	req.Header.Set("Accept", "application/json")
	resp, errDo := client.Do(req)
	if errDo != nil {
		return cluster.BillingModelPriceImportCatalog{}, errDo
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		return cluster.BillingModelPriceImportCatalog{}, fmt.Errorf("models.dev returned HTTP %d", resp.StatusCode)
	}
	raw, errRead := io.ReadAll(io.LimitReader(resp.Body, 32<<20))
	if errRead != nil {
		return cluster.BillingModelPriceImportCatalog{}, errRead
	}
	return parseBillingModelPriceImportCatalog(raw, modelsDevCatalogURL, time.Now().UTC())
}

func parseBillingModelPriceImportCatalog(raw []byte, sourceURL string, fetchedAt time.Time) (cluster.BillingModelPriceImportCatalog, error) {
	var root map[string]any
	if errDecode := json.Unmarshal(raw, &root); errDecode != nil {
		return cluster.BillingModelPriceImportCatalog{}, fmt.Errorf("decode models.dev catalog: %w", errDecode)
	}
	sum := sha256.Sum256(raw)
	catalog := cluster.BillingModelPriceImportCatalog{SourceURL: sourceURL, Version: hex.EncodeToString(sum[:]), FetchedAt: fetchedAt}
	providers := make([]string, 0, len(root))
	for provider := range root {
		providers = append(providers, provider)
	}
	sort.Strings(providers)
	for _, provider := range providers {
		providerValue := root[provider]
		providerRecord, ok := providerValue.(map[string]any)
		if !ok {
			continue
		}
		models, ok := providerRecord["models"].(map[string]any)
		if !ok {
			continue
		}
		modelKeys := make([]string, 0, len(models))
		for model := range models {
			modelKeys = append(modelKeys, model)
		}
		sort.Strings(modelKeys)
		for _, model := range modelKeys {
			modelValue := models[model]
			modelRecord, ok := modelValue.(map[string]any)
			if !ok {
				continue
			}
			costRaw := billingImportRecordValue(modelRecord, "cost", "pricing")
			cost, basePresence, configured := parseBillingModelPriceImportCost(costRaw)
			entry := cluster.BillingModelPriceImportCatalogModel{Provider: provider, Model: billingImportStringValue(modelRecord, "id"), Name: billingImportStringValue(modelRecord, "name"), Cost: cost, InvalidPriceFields: billingImportInvalidPriceFields(costRaw), UnsupportedDimensions: billingImportUnsupportedDimensions(costRaw)}
			if entry.Model == "" {
				entry.Model = model
			}
			if entry.Name == "" {
				entry.Name = entry.Model
			}
			if !configured {
				entry.Cost = nil
			}
			entry.ContextBands, entry.ContextBandIssues = parseBillingModelPriceImportContextBands(costRaw, basePresence)
			catalog.Models = append(catalog.Models, entry)
		}
	}
	if len(catalog.Models) == 0 {
		return cluster.BillingModelPriceImportCatalog{}, fmt.Errorf("models.dev catalog has no models")
	}
	return catalog, nil
}

type billingModelPriceImportCostPresence struct {
	Input      bool
	Output     bool
	CacheRead  bool
	CacheWrite bool
	Request    bool
}

func parseBillingModelPriceImportCost(value any) (*cluster.BillingModelPriceImportCost, billingModelPriceImportCostPresence, bool) {
	record, ok := value.(map[string]any)
	if !ok {
		return nil, billingModelPriceImportCostPresence{}, false
	}
	input, hasInput := billingImportNumberValue(record, "input", "input_price", "inputPrice")
	output, hasOutput := billingImportNumberValue(record, "output", "output_price", "outputPrice")
	cacheRead, hasCacheRead := billingImportNumberValue(record, "cache_read", "cacheRead", "cache_read_price")
	cacheWrite, hasCacheWrite := billingImportNumberValue(record, "cache_write", "cacheWrite", "cache_write_price")
	request, hasRequest := billingImportNumberValue(record, "request", "request_price", "requestPrice")
	if !hasInput && !hasOutput && !hasCacheRead && !hasCacheWrite && !hasRequest {
		return nil, billingModelPriceImportCostPresence{}, false
	}
	if hasInput {
		if !hasCacheRead {
			cacheRead = input * modelsDevDefaultCacheReadInputRatio
			hasCacheRead = true
		}
		if !hasCacheWrite {
			cacheWrite = input * modelsDevDefaultCacheWriteInputRatio
			hasCacheWrite = true
		}
	}
	return &cluster.BillingModelPriceImportCost{Input: input, Output: output, CacheRead: cacheRead, CacheWrite: cacheWrite, Request: request}, billingModelPriceImportCostPresence{Input: hasInput, Output: hasOutput, CacheRead: hasCacheRead, CacheWrite: hasCacheWrite, Request: hasRequest}, true
}

func parseBillingModelPriceImportContextBands(value any, base billingModelPriceImportCostPresence) ([]cluster.BillingModelPriceImportContextBand, []string) {
	record, ok := value.(map[string]any)
	if !ok {
		return nil, nil
	}
	var bands []cluster.BillingModelPriceImportContextBand
	var issues []string
	if rawTiers, exists := record["tiers"]; exists {
		switch tiers := rawTiers.(type) {
		case []any:
			for _, item := range tiers {
				itemRecord, ok := item.(map[string]any)
				if !ok {
					issues = append(issues, "invalid_context_band")
					continue
				}
				tier, ok := itemRecord["tier"].(map[string]any)
				if !ok {
					issues = append(issues, "invalid_context_band_metadata")
					continue
				}
				size, validSize := billingImportNumberValue(tier, "size")
				if !validSize || size < 0 || math.Trunc(size) != size {
					issues = append(issues, "invalid_context_band_boundary")
					continue
				}
				cost, presence, configured := parseBillingModelPriceImportCost(itemRecord)
				invalidFields := billingImportInvalidPriceFields(itemRecord)
				if !configured {
					if len(invalidFields) > 0 {
						issues = append(issues, "invalid_context_band_prices")
					} else {
						issues = append(issues, "missing_context_band_prices")
					}
					continue
				}
				band := cluster.BillingModelPriceImportContextBand{MinInputTokens: int64(size) + 1, Cost: *cost, InvalidPriceFields: invalidFields, UnsupportedDimensions: billingImportUnsupportedDimensions(itemRecord), MissingPriceFields: billingImportMissingTierPriceFields(base, presence)}
				if tierType := strings.TrimSpace(billingImportStringValue(tier, "type")); tierType != "context" {
					band.UnsupportedDimensions = append(band.UnsupportedDimensions, "unsupported_tier_type")
				}
				bands = append(bands, band)
			}
		case map[string]any:
			for boundary, value := range tiers {
				upper, errBoundary := strconv.ParseInt(strings.TrimSpace(boundary), 10, 64)
				if errBoundary != nil || upper < 0 {
					issues = append(issues, "invalid_context_band_boundary")
					continue
				}
				if nested, ok := value.(map[string]any); ok {
					if wrapped := billingImportRecordValue(nested, "cost", "pricing"); wrapped != nil {
						value = wrapped
					}
				}
				cost, presence, configured := parseBillingModelPriceImportCost(value)
				bandRecord, _ := value.(map[string]any)
				invalidFields := billingImportInvalidPriceFields(bandRecord)
				if !configured {
					if len(invalidFields) > 0 {
						issues = append(issues, "invalid_context_band_prices")
					} else {
						issues = append(issues, "missing_context_band_prices")
					}
					continue
				}
				bands = append(bands, cluster.BillingModelPriceImportContextBand{MinInputTokens: upper + 1, Cost: *cost, InvalidPriceFields: invalidFields, UnsupportedDimensions: billingImportUnsupportedDimensions(bandRecord), MissingPriceFields: billingImportMissingTierPriceFields(base, presence)})
			}
		case nil:
		default:
			issues = append(issues, "invalid_context_bands")
		}
	}
	if len(bands) == 0 && len(issues) == 0 {
		if over, ok := record["context_over_200k"]; ok {
			cost, presence, configured := parseBillingModelPriceImportCost(over)
			overRecord, _ := over.(map[string]any)
			invalidFields := billingImportInvalidPriceFields(overRecord)
			if !configured {
				if len(invalidFields) > 0 {
					issues = append(issues, "invalid_context_band_prices")
				} else {
					issues = append(issues, "missing_context_band_prices")
				}
			} else {
				bands = append(bands, cluster.BillingModelPriceImportContextBand{MinInputTokens: 200001, Cost: *cost, InvalidPriceFields: invalidFields, UnsupportedDimensions: billingImportUnsupportedDimensions(overRecord), MissingPriceFields: billingImportMissingTierPriceFields(base, presence)})
			}
		}
	}
	return bands, billingImportUniqueStrings(issues)
}

func billingImportMissingTierPriceFields(base, tier billingModelPriceImportCostPresence) []string {
	missing := make([]string, 0, 5)
	for _, field := range []struct {
		name string
		base bool
		tier bool
	}{
		{name: "input", base: base.Input, tier: tier.Input},
		{name: "output", base: base.Output, tier: tier.Output},
		{name: "cache_read", base: base.CacheRead, tier: tier.CacheRead},
		{name: "cache_write", base: base.CacheWrite, tier: tier.CacheWrite},
		{name: "request", base: base.Request, tier: tier.Request},
	} {
		if field.base && !field.tier {
			missing = append(missing, field.name)
		}
	}
	return missing
}

func billingImportInvalidPriceFields(value any) []string {
	record, ok := value.(map[string]any)
	if !ok {
		return nil
	}
	fields := billingImportPriceFields()
	var invalid []string
	for _, field := range fields {
		name, aliases := field.name, field.aliases
		if billingImportHasMalformedNumber(record, aliases...) {
			invalid = append(invalid, name)
			continue
		}
		value, exists := billingImportNumberValue(record, aliases...)
		if exists && (!isFiniteBillingImportNumber(value) || value < 0) {
			invalid = append(invalid, name)
		}
	}
	return invalid
}

func billingImportUnsupportedDimensions(value any) []string {
	record, ok := value.(map[string]any)
	if !ok {
		return nil
	}
	var unsupported []string
	for _, field := range []string{"image", "input_image", "output_image", "audio", "input_audio", "output_audio", "video", "reasoning"} {
		raw, exists := record[field]
		if !exists || raw == nil {
			continue
		}
		value, exists := billingImportNumberValue(record, field)
		if !exists || !isFiniteBillingImportNumber(value) || value != 0 {
			unsupported = append(unsupported, field)
		}
	}
	return unsupported
}

func billingImportRecordValue(record map[string]any, keys ...string) any {
	for _, key := range keys {
		if value, ok := record[key]; ok {
			return value
		}
	}
	return nil
}
func billingImportStringValue(record map[string]any, keys ...string) string {
	for _, key := range keys {
		if value, ok := record[key].(string); ok && strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}
func billingImportNumberValue(record map[string]any, keys ...string) (float64, bool) {
	for _, key := range keys {
		value, exists := record[key]
		if !exists || value == nil {
			continue
		}
		switch value := value.(type) {
		case float64:
			return value, true
		case int:
			return float64(value), true
		case int64:
			return float64(value), true
		case json.Number:
			parsed, err := value.Float64()
			if err == nil {
				return parsed, true
			}
		case string:
			parsed, err := strconv.ParseFloat(strings.TrimSpace(value), 64)
			if err == nil {
				return parsed, true
			}
		}
	}
	return 0, false
}

type billingImportPriceField struct {
	name    string
	aliases []string
}

func billingImportPriceFields() []billingImportPriceField {
	return []billingImportPriceField{
		{name: "input", aliases: []string{"input", "input_price", "inputPrice"}},
		{name: "output", aliases: []string{"output", "output_price", "outputPrice"}},
		{name: "cache_read", aliases: []string{"cache_read", "cacheRead", "cache_read_price"}},
		{name: "cache_write", aliases: []string{"cache_write", "cacheWrite", "cache_write_price"}},
		{name: "request", aliases: []string{"request", "request_price", "requestPrice"}},
	}
}

func billingImportHasMalformedNumber(record map[string]any, keys ...string) bool {
	for _, key := range keys {
		value, exists := record[key]
		if !exists || value == nil {
			continue
		}
		if _, valid := billingImportNumberValue(map[string]any{key: value}, key); !valid {
			return true
		}
	}
	return false
}

func billingImportUniqueStrings(values []string) []string {
	seen := make(map[string]struct{}, len(values))
	result := make([]string, 0, len(values))
	for _, value := range values {
		if value == "" {
			continue
		}
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}
func isFiniteBillingImportNumber(value float64) bool {
	return !math.IsNaN(value) && !math.IsInf(value, 0)
}
