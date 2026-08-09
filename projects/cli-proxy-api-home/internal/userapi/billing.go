package userapi

import (
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/router-for-me/CLIProxyAPIHome/internal/cluster"
)

const (
	userBillingDefaultLimit         = 50
	userBillingMaxLimit             = 200
	userBillingMinUnixSeconds int64 = 946684800    // 2000-01-01T00:00:00Z
	userBillingMaxUnixSeconds int64 = 253402300799 // 9999-12-31T23:59:59Z
)

// CurrentUserBillingOverview returns the billing overview for the authenticated user.
func (h *Handler) CurrentUserBillingOverview(c *gin.Context) {
	from, to, ok := userBillingDateRangeFromRequest(c)
	if !ok {
		return
	}

	ctx, cancel := requestContext(c)
	defer cancel()
	user, ok := h.authenticatedUser(c, ctx, authFields{})
	if !ok {
		return
	}

	overview, errOverview := h.repo.BillingOverview(ctx, cluster.BillingOverviewQuery{
		From:        from,
		ToExclusive: to,
		UserID:      &user.ID,
	})
	if errOverview != nil {
		respondError(c, http.StatusInternalServerError, "billing_overview_load_failed", errOverview)
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"overview": currentUserBillingOverviewResponse(user, overview),
	})
}

// ListCurrentUserBillingCharges returns billing charges for the authenticated user.
func (h *Handler) ListCurrentUserBillingCharges(c *gin.Context) {
	from, to, ok := userBillingDateRangeFromRequest(c)
	if !ok {
		return
	}
	limit, offset, ok := userBillingPaginationFromRequest(c)
	if !ok {
		return
	}

	ctx, cancel := requestContext(c)
	defer cancel()
	user, ok := h.authenticatedUser(c, ctx, authFields{})
	if !ok {
		return
	}

	result, errCharges := h.repo.ListBillingCharges(ctx, cluster.BillingChargeQuery{
		From:        from,
		ToExclusive: to,
		UserID:      &user.ID,
		Limit:       limit,
		Offset:      offset,
	})
	if errCharges != nil {
		respondError(c, http.StatusInternalServerError, "billing_charge_load_failed", errCharges)
		return
	}
	items := make([]gin.H, 0, len(result.Records))
	for index := range result.Records {
		items = append(items, currentUserBillingChargeResponse(&result.Records[index]))
	}
	c.JSON(http.StatusOK, gin.H{
		"items":  items,
		"total":  result.Total,
		"limit":  limit,
		"offset": offset,
	})
}

func currentUserBillingOverviewResponse(user *cluster.UserRecord, overview cluster.BillingOverview) gin.H {
	currentBalance := 0.0
	if user != nil {
		currentBalance = user.Credits
	}
	return gin.H{
		"current_balance": currentBalance,
		"today_spend":     overview.TotalChargeAmount,
		"month_spend":     overview.TotalChargeAmount,
		"top_models":      currentUserBillingTopItemsResponse(overview.TopModels),
	}
}

func currentUserBillingTopItemsResponse(items []cluster.BillingTopItem) []gin.H {
	response := make([]gin.H, 0, len(items))
	for _, item := range items {
		response = append(response, gin.H{
			"id":            item.ID,
			"label":         item.Label,
			"amount":        item.Amount,
			"request_count": item.RequestCount,
		})
	}
	return response
}

func currentUserBillingChargeResponse(record *cluster.BillingChargeRecord) gin.H {
	if record == nil {
		return gin.H{}
	}
	return gin.H{
		"id":            record.ID,
		"created_at":    record.CreatedAt,
		"provider":      record.Provider,
		"model":         record.Model,
		"input_tokens":  record.InputTokens,
		"output_tokens": record.OutputTokens,
		"amount":        record.Amount,
		"balance_after": record.BalanceAfter,
		"request_id":    record.RequestID,
	}
}

func userBillingDateRangeFromRequest(c *gin.Context) (*time.Time, *time.Time, bool) {
	from, ok := userBillingDateQuery(c, "from", false)
	if !ok {
		return nil, nil, false
	}
	to, ok := userBillingDateQuery(c, "to", true)
	if !ok {
		return nil, nil, false
	}
	if from != nil && to != nil && from.After(*to) {
		respondError(c, http.StatusBadRequest, "invalid_time_range", fmt.Errorf("from must not be after to"))
		return nil, nil, false
	}
	return from, to, true
}

func userBillingDateQuery(c *gin.Context, key string, dateOnlyEndExclusive bool) (*time.Time, bool) {
	raw := strings.TrimSpace(c.Query(key))
	if raw == "" {
		return nil, true
	}
	parsed, dateOnly, errParse := parseUserBillingTime(raw)
	if errParse != nil {
		respondError(c, http.StatusBadRequest, "invalid_"+key, fmt.Errorf("%s must be YYYY-MM-DD, RFC3339, or unix seconds", key))
		return nil, false
	}
	parsed = parsed.UTC()
	if dateOnlyEndExclusive && dateOnly {
		parsed = time.Date(parsed.Year(), parsed.Month(), parsed.Day()+1, 0, 0, 0, 0, time.UTC)
	}
	return &parsed, true
}

func parseUserBillingTime(raw string) (time.Time, bool, error) {
	if parsed, errDate := time.ParseInLocation(time.DateOnly, raw, time.UTC); errDate == nil {
		return parsed, true, nil
	}
	if parsed, errRFC3339 := time.Parse(time.RFC3339Nano, raw); errRFC3339 == nil {
		return parsed, false, nil
	}
	if unixSeconds, errUnix := strconv.ParseInt(raw, 10, 64); errUnix == nil {
		if unixSeconds >= userBillingMinUnixSeconds && unixSeconds <= userBillingMaxUnixSeconds {
			return time.Unix(unixSeconds, 0).UTC(), false, nil
		}
	}
	return time.Time{}, false, fmt.Errorf("time must be YYYY-MM-DD, RFC3339, or unix seconds")
}

func userBillingPaginationFromRequest(c *gin.Context) (int, int, bool) {
	limit, ok := userBillingLimitFromRequest(c)
	if !ok {
		return 0, 0, false
	}
	offset, ok := userBillingOffsetFromRequest(c)
	if !ok {
		return 0, 0, false
	}
	return limit, offset, true
}

func userBillingLimitFromRequest(c *gin.Context) (int, bool) {
	raw := strings.TrimSpace(c.Query("limit"))
	if raw == "" {
		return userBillingDefaultLimit, true
	}
	limit, errParse := strconv.Atoi(raw)
	if errParse != nil || limit <= 0 {
		respondError(c, http.StatusBadRequest, "invalid_limit", fmt.Errorf("limit must be a positive integer"))
		return 0, false
	}
	if limit > userBillingMaxLimit {
		limit = userBillingMaxLimit
	}
	return limit, true
}

func userBillingOffsetFromRequest(c *gin.Context) (int, bool) {
	raw := strings.TrimSpace(c.Query("offset"))
	if raw == "" {
		return 0, true
	}
	offset, errParse := strconv.Atoi(raw)
	if errParse != nil || offset < 0 {
		respondError(c, http.StatusBadRequest, "invalid_offset", fmt.Errorf("offset must be a non-negative integer"))
		return 0, false
	}
	return offset, true
}
