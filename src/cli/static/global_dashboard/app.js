document.addEventListener('DOMContentLoaded', () => {
    // Mock data for the dashboard
    const data = {
        activeAgents: 14,
        tokenSpend: 42.50,
        successRate: 98.2,
        agents: [
            { id: 'agent-alpha', status: 'running', task: 'Phase 4 implementation', spend: 2.10 },
            { id: 'agent-beta', status: 'idle', task: 'Waiting for PR review', spend: 0.50 },
            { id: 'agent-gamma', status: 'running', task: 'Security audit', spend: 5.30 },
            { id: 'agent-delta', status: 'running', task: 'Memory indexing', spend: 1.20 }
        ]
    };

    // Animate numbers
    const animateValue = (id, start, end, duration, isCurrency = false, isPercentage = false) => {
        const obj = document.getElementById(id);
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            let current = progress * (end - start) + start;
            
            if (isCurrency) {
                obj.innerHTML = `$${current.toFixed(2)}`;
            } else if (isPercentage) {
                obj.innerHTML = `${current.toFixed(1)}%`;
            } else {
                obj.innerHTML = Math.floor(current);
            }
            
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    };

    animateValue("active-agents", 0, data.activeAgents, 1500);
    animateValue("token-spend", 0, data.tokenSpend, 1500, true);
    animateValue("success-rate", 0, data.successRate, 1500, false, true);

    // Populate table
    const tbody = document.querySelector('#agents-table tbody');
    data.agents.forEach(agent => {
        const tr = document.createElement('tr');
        const statusClass = agent.status === 'running' ? 'status-running' : 'status-idle';
        
        tr.innerHTML = `
            <td><strong>${agent.id}</strong></td>
            <td><span class="status-badge ${statusClass}">${agent.status.toUpperCase()}</span></td>
            <td>${agent.task}</td>
            <td>$${agent.spend.toFixed(2)}</td>
        `;
        
        // Add micro-animation for row insertion
        tr.style.opacity = '0';
        tr.style.transform = 'translateX(-10px)';
        tbody.appendChild(tr);
        
        setTimeout(() => {
            tr.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            tr.style.opacity = '1';
            tr.style.transform = 'translateX(0)';
        }, 100 + (Math.random() * 300));
    });
});
