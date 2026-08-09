package management

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
	"github.com/router-for-me/CLIProxyAPIHome/internal/proxyutil"
	log "github.com/sirupsen/logrus"
	"gorm.io/gorm"
)

const proxyPoolTestURL = "https://www.google.com/generate_204"

type proxyPoolRequest struct {
	Name     *string `json:"name"`
	ProxyURL *string `json:"proxy_url"`
	Enabled  *bool   `json:"enabled"`
	Scope    *string `json:"scope"`
	Priority *int    `json:"priority"`
	Note     *string `json:"note"`
}

func (h *Handler) ListProxyPoolItems(c *gin.Context) {
	ctx, cancel := h.requestContext(c)
	defer cancel()

	records, errRecords := h.repo.ListProxyPoolItems(ctx)
	if errRecords != nil {
		respondError(c, http.StatusInternalServerError, "proxy_pool_load_failed", errRecords)
		return
	}
	items := make([]gin.H, 0, len(records))
	for index := range records {
		items = append(items, proxyPoolResponse(&records[index]))
	}
	c.JSON(http.StatusOK, gin.H{"items": items})
}

func (h *Handler) CreateProxyPoolItem(c *gin.Context) {
	var body proxyPoolRequest
	if errBind := c.ShouldBindJSON(&body); errBind != nil {
		respondError(c, http.StatusBadRequest, "invalid_body", errBind)
		return
	}
	update := proxyPoolUpdateFromCreateRequest(body)

	ctx, cancel := h.requestContext(c)
	defer cancel()
	record, errCreate := h.repo.CreateProxyPoolItem(ctx, update)
	if errCreate != nil {
		respondError(c, http.StatusBadRequest, "invalid_body", errCreate)
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok", "proxy_pool": proxyPoolResponse(record)})
}

func (h *Handler) UpdateProxyPoolItem(c *gin.Context) {
	var body proxyPoolRequest
	if errBind := c.ShouldBindJSON(&body); errBind != nil {
		respondError(c, http.StatusBadRequest, "invalid_body", errBind)
		return
	}
	patch := proxyPoolPatchFromRequest(body)

	ctx, cancel := h.requestContext(c)
	defer cancel()
	record, errUpdate := h.repo.PatchProxyPoolItem(ctx, c.Param("id"), patch)
	if errUpdate != nil {
		if errors.Is(errUpdate, gorm.ErrRecordNotFound) {
			respondError(c, http.StatusNotFound, "proxy_pool_not_found", errUpdate)
			return
		}
		respondError(c, http.StatusBadRequest, "invalid_body", errUpdate)
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok", "proxy_pool": proxyPoolResponse(record)})
}

func (h *Handler) DeleteProxyPoolItem(c *gin.Context) {
	ctx, cancel := h.requestContext(c)
	defer cancel()

	if errDelete := h.repo.DeleteProxyPoolItem(ctx, c.Param("id")); errDelete != nil {
		if errors.Is(errDelete, gorm.ErrRecordNotFound) {
			respondError(c, http.StatusNotFound, "proxy_pool_not_found", errDelete)
			return
		}
		respondError(c, http.StatusInternalServerError, "proxy_pool_delete_failed", errDelete)
		return
	}
	respondOK(c)
}

func (h *Handler) TestProxyPoolItem(c *gin.Context) {
	ctx, cancel := h.requestContext(c)
	defer cancel()

	record, errGet := h.repo.GetProxyPoolItem(ctx, c.Param("id"))
	if errGet != nil {
		if errors.Is(errGet, gorm.ErrRecordNotFound) {
			respondError(c, http.StatusNotFound, "proxy_pool_not_found", errGet)
			return
		}
		respondError(c, http.StatusInternalServerError, "proxy_pool_load_failed", errGet)
		return
	}

	result, message := testProxyPoolURL(ctx, record.ProxyURL)
	testedAt := time.Now().UTC()
	if _, errMark := h.repo.MarkProxyPoolTestResult(ctx, record.ID, result, testedAt); errMark != nil {
		respondError(c, http.StatusInternalServerError, "proxy_pool_test_result_update_failed", errMark)
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok", "result": result, "message": message})
}

func proxyPoolUpdateFromCreateRequest(body proxyPoolRequest) cluster.ProxyPoolUpdate {
	update := cluster.ProxyPoolUpdate{
		Enabled: body.Enabled,
	}
	if body.Name != nil {
		update.Name = strings.TrimSpace(*body.Name)
	}
	if body.ProxyURL != nil {
		update.ProxyURL = strings.TrimSpace(*body.ProxyURL)
	}
	if body.Scope != nil {
		update.Scope = strings.TrimSpace(*body.Scope)
	}
	if body.Priority != nil {
		update.Priority = *body.Priority
	}
	if body.Note != nil {
		update.Note = strings.TrimSpace(*body.Note)
	}
	return update
}

func proxyPoolPatchFromRequest(body proxyPoolRequest) cluster.ProxyPoolPatch {
	return cluster.ProxyPoolPatch{
		Name:     body.Name,
		ProxyURL: body.ProxyURL,
		Enabled:  body.Enabled,
		Scope:    body.Scope,
		Priority: body.Priority,
		Note:     body.Note,
	}
}

func proxyPoolResponse(record *cluster.ProxyPoolRecord) gin.H {
	if record == nil {
		return gin.H{}
	}
	return gin.H{
		"id":               record.ID,
		"name":             record.Name,
		"proxy_url":        record.ProxyURL,
		"enabled":          record.Enabled,
		"scope":            record.Scope,
		"priority":         record.Priority,
		"last_tested_at":   record.LastTestedAt,
		"last_test_result": record.LastTestResult,
		"note":             record.Note,
		"updated_at":       record.UpdatedAt,
	}
}

func testProxyPoolURL(ctx context.Context, proxyURL string) (string, string) {
	transport, _, errTransport := proxyutil.BuildHTTPTransport(proxyURL)
	if errTransport != nil {
		return cluster.ProxyPoolTestResultFailed, fmt.Sprintf("build proxy transport failed: %v", errTransport)
	}
	client := &http.Client{
		Transport: transport,
		Timeout:   5 * time.Second,
	}
	testCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	req, errRequest := http.NewRequestWithContext(testCtx, http.MethodGet, proxyPoolTestURL, nil)
	if errRequest != nil {
		return cluster.ProxyPoolTestResultFailed, fmt.Sprintf("build proxy test request failed: %v", errRequest)
	}
	resp, errDo := client.Do(req)
	if errDo != nil {
		return cluster.ProxyPoolTestResultFailed, fmt.Sprintf("proxy test request failed: %v", errDo)
	}
	defer func() {
		if errClose := resp.Body.Close(); errClose != nil {
			log.WithError(errClose).Warn("close proxy pool test response body failed")
		}
	}()
	if resp.StatusCode >= http.StatusOK && resp.StatusCode < http.StatusBadRequest {
		return cluster.ProxyPoolTestResultPassed, fmt.Sprintf("proxy test returned HTTP %d", resp.StatusCode)
	}
	return cluster.ProxyPoolTestResultFailed, fmt.Sprintf("proxy test returned HTTP %d", resp.StatusCode)
}
