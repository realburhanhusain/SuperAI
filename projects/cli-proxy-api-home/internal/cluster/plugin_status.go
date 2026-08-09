package cluster

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/router-for-me/CLIProxyAPIHome/internal/node"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const (
	pluginStatusTaskDelete        = "plugin-delete"
	pluginStatusAckPluginIDPrefix = "__task_ack__:"
)

// ReplacePluginStatus stores the latest plugin task status for one node.
func (r *Repository) ReplacePluginStatus(ctx context.Context, nodeType string, status node.PluginTaskStatus) error {
	db, errDB := r.database()
	if errDB != nil {
		return errDB
	}
	nodeType, errType := normalizePluginStatusNodeType(nodeType)
	if errType != nil {
		return errType
	}
	status.NodeID = strings.TrimSpace(status.NodeID)
	if status.NodeID == "" {
		return fmt.Errorf("plugin status node id is required")
	}
	status.NodeType = nodeType
	now := time.Now().UTC()
	if status.UpdatedAt.IsZero() {
		status.UpdatedAt = now
	}
	pluginIDs := pluginStatusPluginIDs(status.Plugins)

	return db.WithContext(contextOrBackground(ctx)).Transaction(func(tx *gorm.DB) error {
		if !pluginStatusIsDeleteReport(status) {
			deleteQuery := tx.
				Where("node_type = ? AND node_id = ?", nodeType, status.NodeID).
				Where("plugin_id NOT LIKE ?", pluginStatusAckPluginIDPrefix+"%")
			if len(pluginIDs) > 0 {
				deleteQuery = deleteQuery.Where("plugin_id NOT IN ?", pluginIDs)
			}
			if errDelete := deleteQuery.Delete(&PluginStatusRecord{}).Error; errDelete != nil {
				return errDelete
			}
		}
		for _, plugin := range status.Plugins {
			record, okRecord := pluginStatusRecordFromTask(nodeType, status, plugin)
			if !okRecord {
				continue
			}
			if errCreate := tx.Clauses(clause.OnConflict{
				Columns: []clause.Column{
					{Name: "node_type"},
					{Name: "node_id"},
					{Name: "plugin_id"},
				},
				DoUpdates: clause.AssignmentColumns([]string{
					"task_id",
					"client_ip",
					"schema_version",
					"task",
					"task_status",
					"phase",
					"ok",
					"task_error",
					"started_at",
					"finished_at",
					"reported_at",
					"goos",
					"goarch",
					"version",
					"release_tag",
					"repository",
					"install_status",
					"load_status",
					"path",
					"skipped",
					"overwritten",
					"plugin_error",
					"updated_at",
				}),
			}).Create(&record).Error; errCreate != nil {
				return errCreate
			}
		}
		if status.TaskID > 0 {
			record := pluginStatusAckRecordFromTask(nodeType, status)
			if errCreate := tx.Clauses(clause.OnConflict{
				Columns: []clause.Column{
					{Name: "node_type"},
					{Name: "node_id"},
					{Name: "plugin_id"},
				},
				DoUpdates: clause.AssignmentColumns([]string{
					"task_id",
					"client_ip",
					"schema_version",
					"task",
					"task_status",
					"phase",
					"ok",
					"task_error",
					"started_at",
					"finished_at",
					"reported_at",
					"updated_at",
				}),
			}).Create(&record).Error; errCreate != nil {
				return errCreate
			}
		}
		return nil
	})
}

// ListPluginStatuses returns the latest plugin task statuses grouped by node and report.
func (r *Repository) ListPluginStatuses(ctx context.Context, nodeType string) ([]node.PluginTaskStatus, error) {
	db, errDB := r.database()
	if errDB != nil {
		return nil, errDB
	}
	nodeType = strings.TrimSpace(strings.ToLower(nodeType))
	if nodeType != "" {
		var errType error
		nodeType, errType = normalizePluginStatusNodeType(nodeType)
		if errType != nil {
			return nil, errType
		}
	}
	query := db.WithContext(contextOrBackground(ctx)).
		Where("plugin_id NOT LIKE ?", pluginStatusAckPluginIDPrefix+"%").
		Order("node_type, node_id, reported_at DESC, task_id DESC, plugin_id")
	if nodeType != "" {
		query = query.Where("node_type = ?", nodeType)
	}
	var records []PluginStatusRecord
	if errFind := query.Find(&records).Error; errFind != nil {
		return nil, errFind
	}
	return pluginTaskStatusesFromRecords(records), nil
}

func normalizePluginStatusNodeType(nodeType string) (string, error) {
	nodeType = strings.TrimSpace(strings.ToLower(nodeType))
	switch nodeType {
	case node.PluginStatusNodeTypeCPA, node.PluginStatusNodeTypeHome:
		return nodeType, nil
	default:
		return "", fmt.Errorf("unsupported plugin status node type %q", nodeType)
	}
}

func pluginStatusIsDeleteReport(status node.PluginTaskStatus) bool {
	return strings.EqualFold(strings.TrimSpace(status.Task), pluginStatusTaskDelete)
}

func pluginStatusAckPluginID(taskID uint) string {
	if taskID == 0 {
		return ""
	}
	return fmt.Sprintf("%s%d", pluginStatusAckPluginIDPrefix, taskID)
}

func pluginStatusPluginIDs(plugins []node.PluginTaskPlugin) []string {
	ids := make([]string, 0, len(plugins))
	seen := make(map[string]struct{}, len(plugins))
	for _, plugin := range plugins {
		id := strings.TrimSpace(plugin.ID)
		if id == "" {
			continue
		}
		if _, ok := seen[id]; ok {
			continue
		}
		seen[id] = struct{}{}
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func pluginStatusRecordFromTask(nodeType string, status node.PluginTaskStatus, plugin node.PluginTaskPlugin) (PluginStatusRecord, bool) {
	pluginID := strings.TrimSpace(plugin.ID)
	if pluginID == "" {
		return PluginStatusRecord{}, false
	}
	var finishedAt *time.Time
	if !status.FinishedAt.IsZero() {
		value := status.FinishedAt.UTC()
		finishedAt = &value
	}
	return PluginStatusRecord{
		NodeType:      nodeType,
		NodeID:        strings.TrimSpace(status.NodeID),
		PluginID:      pluginID,
		TaskID:        status.TaskID,
		ClientIP:      strings.TrimSpace(status.ClientIP),
		SchemaVersion: status.SchemaVersion,
		Task:          strings.TrimSpace(status.Task),
		TaskStatus:    strings.TrimSpace(status.Status),
		Phase:         strings.TrimSpace(status.Phase),
		OK:            status.OK,
		TaskError:     strings.TrimSpace(status.Error),
		StartedAt:     status.StartedAt.UTC(),
		FinishedAt:    finishedAt,
		ReportedAt:    status.UpdatedAt.UTC(),
		GOOS:          strings.TrimSpace(status.Platform.GOOS),
		GOARCH:        strings.TrimSpace(status.Platform.GOARCH),
		Version:       strings.TrimSpace(plugin.Version),
		ReleaseTag:    strings.TrimSpace(plugin.ReleaseTag),
		Repository:    strings.TrimSpace(plugin.Repository),
		InstallStatus: strings.TrimSpace(plugin.InstallStatus),
		LoadStatus:    strings.TrimSpace(plugin.LoadStatus),
		Path:          strings.TrimSpace(plugin.Path),
		Skipped:       plugin.Skipped,
		Overwritten:   plugin.Overwritten,
		PluginError:   strings.TrimSpace(plugin.Error),
	}, true
}

func pluginStatusAckRecordFromTask(nodeType string, status node.PluginTaskStatus) PluginStatusRecord {
	var finishedAt *time.Time
	if !status.FinishedAt.IsZero() {
		value := status.FinishedAt.UTC()
		finishedAt = &value
	}
	return PluginStatusRecord{
		NodeType:      nodeType,
		NodeID:        strings.TrimSpace(status.NodeID),
		PluginID:      pluginStatusAckPluginID(status.TaskID),
		TaskID:        status.TaskID,
		ClientIP:      strings.TrimSpace(status.ClientIP),
		SchemaVersion: status.SchemaVersion,
		Task:          strings.TrimSpace(status.Task),
		TaskStatus:    strings.TrimSpace(status.Status),
		Phase:         strings.TrimSpace(status.Phase),
		OK:            status.OK,
		TaskError:     strings.TrimSpace(status.Error),
		StartedAt:     status.StartedAt.UTC(),
		FinishedAt:    finishedAt,
		ReportedAt:    status.UpdatedAt.UTC(),
	}
}

func pluginTaskStatusesFromRecords(records []PluginStatusRecord) []node.PluginTaskStatus {
	statuses := make([]node.PluginTaskStatus, 0)
	index := make(map[pluginTaskStatusRecordGroup]int)
	for _, record := range records {
		if strings.HasPrefix(strings.TrimSpace(record.PluginID), pluginStatusAckPluginIDPrefix) {
			continue
		}
		key := pluginTaskStatusRecordGroupKey(record)
		statusIndex, okStatus := index[key]
		if !okStatus {
			statuses = append(statuses, pluginTaskStatusFromRecord(record))
			statusIndex = len(statuses) - 1
			index[key] = statusIndex
		}
		statuses[statusIndex].Plugins = append(statuses[statusIndex].Plugins, pluginTaskPluginFromRecord(record))
	}
	return statuses
}

type pluginTaskStatusRecordGroup struct {
	nodeType      string
	nodeID        string
	taskID        uint
	clientIP      string
	schemaVersion int
	task          string
	taskStatus    string
	phase         string
	ok            bool
	taskError     string
	startedAt     time.Time
	finishedAt    time.Time
	hasFinishedAt bool
	reportedAt    time.Time
	goos          string
	goarch        string
}

func pluginTaskStatusRecordGroupKey(record PluginStatusRecord) pluginTaskStatusRecordGroup {
	finishedAt := time.Time{}
	hasFinishedAt := false
	if record.FinishedAt != nil {
		finishedAt = record.FinishedAt.UTC()
		hasFinishedAt = true
	}
	return pluginTaskStatusRecordGroup{
		nodeType:      strings.TrimSpace(record.NodeType),
		nodeID:        strings.TrimSpace(record.NodeID),
		taskID:        record.TaskID,
		clientIP:      strings.TrimSpace(record.ClientIP),
		schemaVersion: record.SchemaVersion,
		task:          strings.TrimSpace(record.Task),
		taskStatus:    strings.TrimSpace(record.TaskStatus),
		phase:         strings.TrimSpace(record.Phase),
		ok:            record.OK,
		taskError:     strings.TrimSpace(record.TaskError),
		startedAt:     record.StartedAt.UTC(),
		finishedAt:    finishedAt,
		hasFinishedAt: hasFinishedAt,
		reportedAt:    record.ReportedAt.UTC(),
		goos:          strings.TrimSpace(record.GOOS),
		goarch:        strings.TrimSpace(record.GOARCH),
	}
}

func pluginTaskStatusFromRecord(record PluginStatusRecord) node.PluginTaskStatus {
	finishedAt := time.Time{}
	if record.FinishedAt != nil {
		finishedAt = record.FinishedAt.UTC()
	}
	return node.PluginTaskStatus{
		SchemaVersion: record.SchemaVersion,
		TaskID:        record.TaskID,
		NodeType:      strings.TrimSpace(record.NodeType),
		Task:          strings.TrimSpace(record.Task),
		NodeID:        strings.TrimSpace(record.NodeID),
		ClientIP:      strings.TrimSpace(record.ClientIP),
		Status:        strings.TrimSpace(record.TaskStatus),
		Phase:         strings.TrimSpace(record.Phase),
		OK:            record.OK,
		StartedAt:     record.StartedAt.UTC(),
		FinishedAt:    finishedAt,
		UpdatedAt:     record.ReportedAt.UTC(),
		Platform: node.PluginTaskPlatform{
			GOOS:   strings.TrimSpace(record.GOOS),
			GOARCH: strings.TrimSpace(record.GOARCH),
		},
		Plugins: []node.PluginTaskPlugin{},
		Error:   strings.TrimSpace(record.TaskError),
	}
}

func pluginTaskPluginFromRecord(record PluginStatusRecord) node.PluginTaskPlugin {
	return node.PluginTaskPlugin{
		ID:            strings.TrimSpace(record.PluginID),
		Version:       strings.TrimSpace(record.Version),
		ReleaseTag:    strings.TrimSpace(record.ReleaseTag),
		Repository:    strings.TrimSpace(record.Repository),
		InstallStatus: strings.TrimSpace(record.InstallStatus),
		LoadStatus:    strings.TrimSpace(record.LoadStatus),
		Path:          strings.TrimSpace(record.Path),
		Skipped:       record.Skipped,
		Overwritten:   record.Overwritten,
		Error:         strings.TrimSpace(record.PluginError),
	}
}
