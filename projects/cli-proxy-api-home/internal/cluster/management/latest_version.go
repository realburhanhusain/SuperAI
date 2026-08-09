package management

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	appconfig "github.com/router-for-me/CLIProxyAPIHome/internal/config"
	"github.com/router-for-me/CLIProxyAPIHome/internal/util"
	log "github.com/sirupsen/logrus"
)

const (
	latestReleaseURL       = "https://api.github.com/repos/router-for-me/CLIProxyAPIHome/releases/latest"
	latestReleaseUserAgent = "CLIProxyAPIHome"
)

type releaseInfo struct {
	TagName string `json:"tag_name"`
	Name    string `json:"name"`
}

// GetLatestVersion returns a latest version.
func (h *Handler) GetLatestVersion(c *gin.Context) {
	// Validate request inputs before mutating persisted state.
	if c == nil {
		return
	}
	ctx, cancel := h.requestContext(c)
	defer cancel()

	cfg, _, errConfig := h.currentConfig(ctx)
	if errConfig != nil {
		respondError(c, http.StatusInternalServerError, "config_load_failed", errConfig)
		return
	}

	client := &http.Client{Timeout: 10 * time.Second}
	proxyURL := ""
	if cfg != nil {
		proxyURL = strings.TrimSpace(cfg.ProxyURL)
	}
	if proxyURL != "" {
		util.SetProxy(&appconfig.SDKConfig{ProxyURL: proxyURL}, client)
	}

	req, errNewRequest := http.NewRequestWithContext(ctx, http.MethodGet, latestReleaseURL, nil)
	if errNewRequest != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "request_create_failed", "message": errNewRequest.Error()})
		return
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("User-Agent", latestReleaseUserAgent)

	resp, errDo := client.Do(req)
	if errDo != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "request_failed", "message": errDo.Error()})
		return
	}
	defer func() {
		if errClose := resp.Body.Close(); errClose != nil {
			log.Errorf("latest version response body close error: %v", errClose)
		}
	}()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		c.JSON(http.StatusBadGateway, gin.H{"error": "unexpected_status", "message": fmt.Sprintf("status %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))})
		return
	}

	var info releaseInfo
	if errDecode := json.NewDecoder(resp.Body).Decode(&info); errDecode != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "decode_failed", "message": errDecode.Error()})
		return
	}

	version := strings.TrimSpace(info.TagName)
	if version == "" {
		version = strings.TrimSpace(info.Name)
	}
	if version == "" {
		c.JSON(http.StatusBadGateway, gin.H{"error": "invalid_response", "message": "missing release version"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"latest-version": version})
}
