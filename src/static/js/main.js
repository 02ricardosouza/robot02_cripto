document.addEventListener('DOMContentLoaded', function() {
    // Seleção de elementos
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content > div');
    const alerts = document.getElementById('alerts');
    
    // Tabelas
    const botTable = document.getElementById('bot-table');
    const simulationTable = document.getElementById('simulation-table');
    
    // Formulários
    const botForm = document.getElementById('bot-form');
    const simulationForm = document.getElementById('simulation-form');

    // Configuração de abas
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove a classe active de todas as abas
            tabs.forEach(t => t.classList.remove('active'));
            
            // Adiciona a classe active na aba clicada
            tab.classList.add('active');
            
            // Esconde todos os conteúdos
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Mostra o conteúdo da aba clicada
            const target = tab.getAttribute('data-target');
            document.getElementById(target).classList.add('active');
        });
    });

    // Buscar status dos bots
    function fetchStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                updateBotTable(data.active_bots);
                setTimeout(fetchStatus, 10000); // Atualiza a cada 10 segundos
            })
            .catch(error => {
                console.error('Erro ao buscar status:', error);
                setTimeout(fetchStatus, 30000); // Tentar novamente em 30 segundos em caso de erro
            });
    }

    // Atualizar tabela de bots
    function updateBotTable(bots) {
        const tbody = botTable.querySelector('tbody');
        tbody.innerHTML = '';

        if (bots.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="6" class="text-center">Nenhum bot em execução</td>';
            tbody.appendChild(row);
            return;
        }

        bots.forEach(bot => {
            const row = document.createElement('tr');
            const positionClass = bot.position === 'Comprado' ? 'badge-success' : 'badge-danger';
            
            row.innerHTML = `
                <td>${bot.stock_code}/${bot.operation_code}</td>
                <td><span class="badge ${positionClass}">${bot.position}</span></td>
                <td>${bot.last_buy_price ? bot.last_buy_price.toFixed(2) : '-'}</td>
                <td>${bot.last_sell_price ? bot.last_sell_price.toFixed(2) : '-'}</td>
                <td>${bot.wallet_balance || 0}</td>
                <td>
                    <div class="button-group">
                        <button class="button button-danger btn-stop-bot" data-id="${bot.id}">Parar</button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        // Adicionar eventos aos botões de parar
        const stopButtons = document.querySelectorAll('.btn-stop-bot');
        stopButtons.forEach(button => {
            button.addEventListener('click', function() {
                const botId = this.getAttribute('data-id');
                stopBot(botId);
            });
        });
    }

    // Iniciar um bot
    function startBot(formData) {
        fetch('/api/bot/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert('success', `Bot ${data.bot_id} iniciado com sucesso!`);
                botForm.reset();
                fetchStatus(); // Atualiza a lista de bots
            } else {
                showAlert('danger', `Erro: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Erro ao iniciar bot:', error);
            showAlert('danger', 'Erro ao iniciar bot. Verifique o console para mais detalhes.');
        });
    }

    // Parar um bot
    function stopBot(botId) {
        fetch(`/api/bot/stop/${botId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert('success', data.message);
                fetchStatus(); // Atualiza a lista de bots
            } else {
                showAlert('danger', `Erro: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Erro ao parar bot:', error);
            showAlert('danger', 'Erro ao parar bot. Verifique o console para mais detalhes.');
        });
    }

    // Iniciar simulação
    function startSimulation(formData) {
        fetch('/api/simulation/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert('success', `Simulação ${data.simulation_id} iniciada com sucesso!`);
                simulationForm.reset();
                
                // Adiciona a simulação à lista
                const simId = data.simulation_id;
                addSimulationToTable(simId, formData.stock_code, formData.operation_code);
            } else {
                showAlert('danger', `Erro: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Erro ao iniciar simulação:', error);
            showAlert('danger', 'Erro ao iniciar simulação. Verifique o console para mais detalhes.');
        });
    }

    // Adicionar simulação à tabela
    function addSimulationToTable(simId, stockCode, operationCode) {
        const tbody = simulationTable.querySelector('tbody');
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${simId}</td>
            <td>${stockCode}/${operationCode}</td>
            <td>
                <div class="button-group">
                    <button class="button button-primary btn-execute-sim" data-id="${simId}">Executar</button>
                    <button class="button button-success btn-results-sim" data-id="${simId}">Resultados</button>
                    <button class="button button-danger btn-stop-sim" data-id="${simId}">Parar</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);

        // Adicionar eventos aos botões
        row.querySelector('.btn-execute-sim').addEventListener('click', function() {
            executeSimulation(simId);
        });

        row.querySelector('.btn-results-sim').addEventListener('click', function() {
            showSimulationResults(simId);
        });

        row.querySelector('.btn-stop-sim').addEventListener('click', function() {
            stopSimulation(simId);
        });
    }

    // Executar um passo da simulação
    function executeSimulation(simId) {
        fetch(`/api/simulation/${simId}/execute`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert('success', `Passo executado com sucesso!`);
                // Mostrar os resultados
                showSimulationResults(simId);
            } else {
                showAlert('danger', `Erro: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Erro ao executar simulação:', error);
            showAlert('danger', 'Erro ao executar simulação. Verifique o console para mais detalhes.');
        });
    }

    // Mostrar resultados da simulação
    function showSimulationResults(simId) {
        fetch(`/api/simulation/${simId}/results`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Mostrar resultados em um modal ou em um elemento da página
                    const results = data.results;
                    const modal = document.getElementById('results-modal');
                    const modalContent = document.getElementById('results-content');
                    
                    modalContent.innerHTML = `
                        <h3>Resultados da Simulação: ${simId}</h3>
                        <p><strong>Moeda:</strong> ${data.stock_code}/${data.operation_code}</p>
                        <p><strong>Total de compras:</strong> ${results.buys}</p>
                        <p><strong>Total de vendas:</strong> ${results.sells}</p>
                        <p><strong>Lucro/Prejuízo:</strong> ${results.profit_loss.toFixed(2)} (${results.profit_loss_percentage.toFixed(2)}%)</p>
                        <p><strong>Saldo atual:</strong> ${results.stock_balance}</p>
                        <p><strong>Preço atual:</strong> ${results.current_price.toFixed(2)}</p>
                        
                        <h4>Histórico de operações:</h4>
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Tipo</th>
                                    <th>Preço</th>
                                    <th>Quantidade</th>
                                    <th>Valor Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${results.trades.map(trade => `
                                    <tr>
                                        <td><span class="badge badge-${trade.type === 'BUY' ? 'success' : 'danger'}">${trade.type}</span></td>
                                        <td>${trade.price.toFixed(2)}</td>
                                        <td>${trade.quantity}</td>
                                        <td>${trade.total_value.toFixed(2)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                    
                    modal.style.display = 'block';
                    
                    // Fechar modal ao clicar no X
                    const closeBtn = modal.querySelector('.close');
                    closeBtn.addEventListener('click', function() {
                        modal.style.display = 'none';
                    });
                    
                    // Fechar modal ao clicar fora do conteúdo
                    window.addEventListener('click', function(event) {
                        if (event.target === modal) {
                            modal.style.display = 'none';
                        }
                    });
                } else {
                    showAlert('danger', `Erro: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Erro ao obter resultados da simulação:', error);
                showAlert('danger', 'Erro ao obter resultados. Verifique o console para mais detalhes.');
            });
    }

    // Parar simulação
    function stopSimulation(simId) {
        fetch(`/api/simulation/${simId}/stop`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert('success', data.message);
                
                // Remover da tabela
                const rows = simulationTable.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const rowSimId = row.querySelector('.btn-stop-sim').getAttribute('data-id');
                    if (rowSimId === simId) {
                        row.remove();
                    }
                });
                
                // Mostrar resultados finais
                const results = data.final_results;
                const modal = document.getElementById('results-modal');
                const modalContent = document.getElementById('results-content');
                
                modalContent.innerHTML = `
                    <h3>Resultados Finais da Simulação: ${simId}</h3>
                    <p><strong>Total de compras:</strong> ${results.buys}</p>
                    <p><strong>Total de vendas:</strong> ${results.sells}</p>
                    <p><strong>Lucro/Prejuízo:</strong> ${results.profit_loss.toFixed(2)} (${results.profit_loss_percentage.toFixed(2)}%)</p>
                    
                    <h4>Histórico de operações:</h4>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Tipo</th>
                                <th>Preço</th>
                                <th>Quantidade</th>
                                <th>Valor Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${results.trades.map(trade => `
                                <tr>
                                    <td><span class="badge badge-${trade.type === 'BUY' ? 'success' : 'danger'}">${trade.type}</span></td>
                                    <td>${trade.price.toFixed(2)}</td>
                                    <td>${trade.quantity}</td>
                                    <td>${trade.total_value.toFixed(2)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
                
                modal.style.display = 'block';
            } else {
                showAlert('danger', `Erro: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Erro ao parar simulação:', error);
            showAlert('danger', 'Erro ao parar simulação. Verifique o console para mais detalhes.');
        });
    }

    // Exibir alerta
    function showAlert(type, message) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        alerts.appendChild(alert);
        
        // Remover o alerta após 5 segundos
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }

    // Adicionar eventos aos formulários
    if (botForm) {
        botForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                stock_code: document.getElementById('bot-stock-code').value,
                operation_code: document.getElementById('bot-operation-code').value,
                traded_quantity: parseFloat(document.getElementById('bot-quantity').value),
                volatility_factor: parseFloat(document.getElementById('bot-volatility').value),
                stop_loss_percentage: parseFloat(document.getElementById('bot-stop-loss').value),
                acceptable_loss_percentage: parseFloat(document.getElementById('bot-acceptable-loss').value),
                fallback_activated: document.getElementById('bot-fallback').checked
            };
            
            startBot(formData);
        });
    }

    if (simulationForm) {
        simulationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                stock_code: document.getElementById('sim-stock-code').value,
                operation_code: document.getElementById('sim-operation-code').value,
                traded_quantity: parseFloat(document.getElementById('sim-quantity').value),
                volatility_factor: parseFloat(document.getElementById('sim-volatility').value),
                stop_loss_percentage: parseFloat(document.getElementById('sim-stop-loss').value),
                acceptable_loss_percentage: parseFloat(document.getElementById('sim-acceptable-loss').value),
                fallback_activated: document.getElementById('sim-fallback').checked
            };
            
            startSimulation(formData);
        });
    }

    // Configura modal
    const modal = document.getElementById('results-modal');
    const close = document.querySelector('.close');
    
    if (close && modal) {
        close.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        window.addEventListener('click', (e) => {
            if (e.target == modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    // Aplica ajustes responsivos
    handleResponsiveLayout();
    
    // Monitora redimensionamento da janela
    window.addEventListener('resize', handleResponsiveLayout);
    
    // Carrega dados iniciais
    fetchStatus();
});

// Função para ajustar o layout em dispositivos móveis
function handleResponsiveLayout() {
    const isMobile = window.innerWidth <= 768;
    const isSmallScreen = window.innerWidth <= 480;
    
    // Ajusta o layout das tabelas em dispositivos móveis
    if (isMobile) {
        // Simplifica o cabeçalho das tabelas em telas muito pequenas
        if (isSmallScreen) {
            simplifyTableHeaders();
        } else {
            restoreTableHeaders();
        }
    } else {
        restoreTableHeaders();
    }
}

// Simplifica cabeçalhos de tabela em telas muito pequenas
function simplifyTableHeaders() {
    // Adapta a tabela de bots para telas pequenas
    const botTable = document.getElementById('bot-table');
    if (botTable) {
        const headers = botTable.querySelectorAll('th');
        if (headers.length > 0) {
            // Usa abreviações para cabeçalhos longos
            const headerMap = {
                'Último Preço de Compra': 'Compra',
                'Último Preço de Venda': 'Venda'
            };
            
            headers.forEach(header => {
                if (headerMap[header.textContent]) {
                    header.setAttribute('data-original', header.textContent);
                    header.textContent = headerMap[header.textContent];
                }
            });
        }
    }
}

// Restaura cabeçalhos originais
function restoreTableHeaders() {
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-original]');
        headers.forEach(header => {
            header.textContent = header.getAttribute('data-original');
        });
    });
} 