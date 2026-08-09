package hanlders

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
)

// ListNodes returns a nodes.
func ListNodes(c *gin.Context) {
	if c == nil {
		return
	}
	c.JSON(http.StatusOK, gin.H{"nodes": node.GlobalRegistry().List()})
}
