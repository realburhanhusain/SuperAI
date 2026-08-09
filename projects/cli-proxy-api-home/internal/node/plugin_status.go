package node

import "time"

const (
	PluginStatusNodeTypeCPA  = "cpa"
	PluginStatusNodeTypeHome = "home"

	PluginTaskOperationDelete = "delete"
	PluginTaskTargetAll       = "all"
)

type PluginTaskStatus struct {
	SchemaVersion int                `json:"schema_version"`
	TaskID        uint               `json:"task_id,omitempty"`
	NodeType      string             `json:"node_type,omitempty"`
	Task          string             `json:"task"`
	NodeID        string             `json:"node_id"`
	ClientIP      string             `json:"client_ip,omitempty"`
	Status        string             `json:"status"`
	Phase         string             `json:"phase"`
	OK            bool               `json:"ok"`
	StartedAt     time.Time          `json:"started_at"`
	FinishedAt    time.Time          `json:"finished_at,omitempty"`
	UpdatedAt     time.Time          `json:"updated_at"`
	Platform      PluginTaskPlatform `json:"platform"`
	Plugins       []PluginTaskPlugin `json:"plugins"`
	Error         string             `json:"error,omitempty"`
}

type PluginTask struct {
	ID             uint      `json:"id"`
	Operation      string    `json:"operation"`
	PluginID       string    `json:"plugin_id"`
	TargetNodeType string    `json:"target_node_type,omitempty"`
	TargetNodeID   string    `json:"target_node_id,omitempty"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

type PluginTaskPlatform struct {
	GOOS   string `json:"goos"`
	GOARCH string `json:"goarch"`
}

type PluginTaskPlugin struct {
	ID            string `json:"id"`
	Version       string `json:"version,omitempty"`
	ReleaseTag    string `json:"release_tag,omitempty"`
	Repository    string `json:"repository,omitempty"`
	InstallStatus string `json:"install_status"`
	LoadStatus    string `json:"load_status,omitempty"`
	Path          string `json:"path,omitempty"`
	Skipped       bool   `json:"skipped,omitempty"`
	Overwritten   bool   `json:"overwritten,omitempty"`
	Error         string `json:"error,omitempty"`
}
