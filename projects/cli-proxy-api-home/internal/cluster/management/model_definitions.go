package management

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/registry"
)

// GetAuthFileModels returns an auth file models.
func (h *Handler) GetAuthFileModels(c *gin.Context) {
	// Normalize source data before building the derived payload.
	name := strings.TrimSpace(c.Query("name"))
	if name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
		return
	}

	ctx, cancel := h.requestContext(c)
	defer cancel()
	auths, errAuths := h.repo.ListAuths(ctx)
	if errAuths != nil {
		respondError(c, http.StatusInternalServerError, "auth_load_failed", errAuths)
		return
	}

	authID := ""
	for _, auth := range auths {
		if auth == nil {
			continue
		}
		if auth.ID == name || auth.Index == name || authFileDisplayName(auth) == name || authFileName(auth) == name {
			authID = auth.ID
			break
		}
		if strings.TrimSuffix(name, ".json") == auth.ID {
			authID = auth.ID
			break
		}
	}
	if authID == "" {
		authID = name
	}

	models := registry.GetGlobalRegistry().GetModelsForClient(authID)
	result := make([]gin.H, 0, len(models))
	for _, model := range models {
		if model == nil {
			continue
		}
		entry := gin.H{"id": model.ID}
		if model.DisplayName != "" {
			entry["display_name"] = model.DisplayName
		}
		if model.Type != "" {
			entry["type"] = model.Type
		}
		if model.OwnedBy != "" {
			entry["owned_by"] = model.OwnedBy
		}
		result = append(result, entry)
	}
	c.JSON(http.StatusOK, gin.H{"models": result})
}

// GetModels returns static or currently available model definitions.
func (h *Handler) GetModels(c *gin.Context) {
	scope := strings.ToLower(strings.TrimSpace(firstNonEmptyQuery(c, "scope", "source", "mode", "type")))
	if scope == "" {
		scope = "available"
	}

	switch scope {
	case "available", "active", "current":
		c.JSON(http.StatusOK, gin.H{
			"scope":  "available",
			"models": registry.GetGlobalRegistry().GetAvailableModelDefinitions(),
		})
	case "static", "all-static", "definitions":
		channel := strings.TrimSpace(firstNonEmptyQuery(c, "channel", "provider"))
		if channel == "" {
			c.JSON(http.StatusOK, gin.H{
				"scope":  "static",
				"models": registry.GetAllStaticModelDefinitions(),
			})
			return
		}
		models := registry.GetStaticModelDefinitionsByChannel(channel)
		if models == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "unknown channel", "channel": channel})
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"scope":   "static",
			"channel": strings.ToLower(strings.TrimSpace(channel)),
			"models":  models,
		})
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid scope", "scope": scope})
	}
}

// GetStaticModelDefinitions returns a static model definitions.
func (h *Handler) GetStaticModelDefinitions(c *gin.Context) {
	channel := strings.TrimSpace(c.Param("channel"))
	if channel == "" {
		channel = strings.TrimSpace(c.Query("channel"))
	}
	if channel == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "channel is required"})
		return
	}

	models := registry.GetStaticModelDefinitionsByChannel(channel)
	if models == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown channel", "channel": channel})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"channel": strings.ToLower(strings.TrimSpace(channel)),
		"models":  models,
	})
}
