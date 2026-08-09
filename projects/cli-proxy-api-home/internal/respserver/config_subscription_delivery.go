package respserver

import (
	"context"
	"net"
	"sync"
)

type configSubscriptionDelivery struct {
	ctx     context.Context
	writer  *safeWriter
	ready   <-chan struct{}
	aborted <-chan struct{}

	queueMu sync.Mutex
	tail    <-chan struct{}
}

func newConfigSubscriptionDelivery(
	ctx context.Context,
	writer *safeWriter,
	ready <-chan struct{},
	aborted <-chan struct{},
) *configSubscriptionDelivery {
	if ctx == nil {
		ctx = context.Background()
	}
	queueHead := make(chan struct{})
	close(queueHead)
	return &configSubscriptionDelivery{
		ctx:     ctx,
		writer:  writer,
		ready:   ready,
		aborted: aborted,
		tail:    queueHead,
	}
}

func (d *configSubscriptionDelivery) Write(payload []byte) error {
	if d == nil || d.writer == nil {
		return net.ErrClosed
	}

	done := make(chan struct{})
	d.queueMu.Lock()
	previous := d.tail
	d.tail = done
	d.queueMu.Unlock()
	defer close(done)

	select {
	case <-previous:
	case <-d.ctx.Done():
		return d.ctx.Err()
	}
	if errContext := d.ctx.Err(); errContext != nil {
		return errContext
	}
	select {
	case <-d.ready:
	case <-d.ctx.Done():
		return d.ctx.Err()
	}
	if errContext := d.ctx.Err(); errContext != nil {
		return errContext
	}
	select {
	case <-d.aborted:
		return net.ErrClosed
	default:
	}
	if errContext := d.ctx.Err(); errContext != nil {
		return errContext
	}
	return d.writer.WriteDispatchReply(subscriptionMessage(configSubscriptionChannel, payload))
}
