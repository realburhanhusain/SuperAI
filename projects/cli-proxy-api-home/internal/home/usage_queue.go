package home

import (
	"context"
	"strings"
	"sync"

	log "github.com/sirupsen/logrus"
)

type usagePayloadQueue struct {
	mu     sync.Mutex
	cond   *sync.Cond
	items  []string
	head   int
	closed bool
}

func newUsagePayloadQueue() *usagePayloadQueue {
	q := &usagePayloadQueue{}
	q.cond = sync.NewCond(&q.mu)
	return q
}

func (q *usagePayloadQueue) Push(payload string) bool {
	if q == nil {
		return false
	}

	q.mu.Lock()
	defer q.mu.Unlock()
	if q.closed {
		return false
	}
	q.items = append(q.items, payload)
	q.cond.Signal()
	return true
}

func (q *usagePayloadQueue) Pop() (string, bool) {
	if q == nil {
		return "", false
	}

	q.mu.Lock()
	defer q.mu.Unlock()
	for q.head >= len(q.items) && !q.closed {
		q.cond.Wait()
	}
	if q.closed {
		return "", false
	}

	payload := q.items[q.head]
	q.items[q.head] = ""
	q.head++
	q.compactLocked()
	return payload, true
}

func (q *usagePayloadQueue) Close() {
	if q == nil {
		return
	}

	q.mu.Lock()
	q.closed = true
	q.items = nil
	q.head = 0
	q.cond.Broadcast()
	q.mu.Unlock()
}

func (q *usagePayloadQueue) compactLocked() {
	if q.head < 1024 || q.head*2 < len(q.items) {
		return
	}
	next := append([]string(nil), q.items[q.head:]...)
	q.items = next
	q.head = 0
}

func (r *Runtime) startClusterUsageWriter(ctx context.Context) {
	if r == nil || r.clusterAdapter == nil || !r.clusterAdapter.Enabled() {
		return
	}
	if ctx == nil {
		ctx = context.Background()
	}
	store, ok := r.clusterAdapter.(clusterUsageStore)
	if !ok || store == nil {
		log.Errorf("cluster usage store is unavailable")
		return
	}

	queue := newUsagePayloadQueue()
	r.clusterUsageQueueMu.Lock()
	if r.clusterUsageQueue != nil {
		r.clusterUsageQueueMu.Unlock()
		return
	}
	r.clusterUsageQueue = queue
	r.clusterUsageQueueMu.Unlock()

	go func() {
		<-ctx.Done()
		queue.Close()
	}()
	go r.runClusterUsageWriter(ctx, store, queue)
}

func (r *Runtime) stopClusterUsageWriter() {
	if r == nil {
		return
	}

	r.clusterUsageQueueMu.Lock()
	queue := r.clusterUsageQueue
	r.clusterUsageQueue = nil
	r.clusterUsageQueueMu.Unlock()
	if queue != nil {
		queue.Close()
	}
}

func (r *Runtime) getClusterUsageQueue() *usagePayloadQueue {
	if r == nil {
		return nil
	}

	r.clusterUsageQueueMu.Lock()
	defer r.clusterUsageQueueMu.Unlock()
	return r.clusterUsageQueue
}

func (r *Runtime) runClusterUsageWriter(ctx context.Context, store clusterUsageStore, queue *usagePayloadQueue) {
	if store == nil || queue == nil {
		return
	}

	for {
		payload, ok := queue.Pop()
		if !ok {
			return
		}
		if strings.TrimSpace(payload) == "" {
			continue
		}
		if errStoreUsagePayload := store.StoreUsagePayload(ctx, payload); errStoreUsagePayload != nil {
			log.Errorf("usage database async write error: %v", errStoreUsagePayload)
		}
	}
}
