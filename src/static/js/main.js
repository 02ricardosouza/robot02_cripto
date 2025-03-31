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

        if (!bots || bots.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="6" class="text-center">Nenhum bot em execução</td>';
            tbody.appendChild(row);
            return;
        }

        bots.forEach(bot => {
            const row = document.createElement('tr');
            const positionClass = bot.position === 'Comprado' ? 'badge-success' : 'badge-danger';
            
            // Verificar se os valores são números antes de usar toFixed
            const lastBuyPrice = bot.last_buy_price !== null && bot.last_buy_price !== undefined ? 
                Number(bot.last_buy_price).toFixed(2) : '-';
            const lastSellPrice = bot.last_sell_price !== null && bot.last_sell_price !== undefined ? 
                Number(bot.last_sell_price).toFixed(2) : '-';
            
            row.innerHTML = `
                <td>${bot.stock_code}/${bot.operation_code}</td>
                <td><span class="badge ${positionClass}">${bot.position}</span></td>
                <td>${lastBuyPrice}</td>
                <td>${lastSellPrice}</td>
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
            if (data.success) {
                showAlert('success', `Simulação ${data.simulation_id} iniciada com sucesso!`);
                simulationForm.reset();
                
                // Adiciona a simulação à lista
                const simId = data.simulation_id;
                addSimulationToTable(simId, formData.stock_code, formData.operation_code);
            } else {
                showAlert('danger', `Erro: ${data.error || 'Falha ao iniciar simulação'}`);
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
            if (data.success) {
                showAlert('success', `Passo executado com sucesso!`);
                // Mostrar os resultados
                showSimulationResults(simId);
            } else {
                showAlert('danger', `Erro: ${data.error || 'Falha ao executar simulação'}`);
            }
        })
        .catch(error => {
            console.error('Erro ao executar simulação:', error);
            showAlert('danger', 'Erro ao executar simulação. Verifique o console para mais detalhes.');
        });
    }

    // Mostrar resultados da simulação
    function showSimulationResults(simId) {
        fetch(`/api/simulation/history/${simId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Mostrar resultados em um modal ou em um elemento da página
                    const results = data.statistics;
                    const trades = data.trades || [];
                    const details = data.details || {};
                    
                    const modal = document.getElementById('results-modal');
                    const modalContent = document.getElementById('results-content');
                    
                    // Função auxiliar para formatar números com segurança
                    const safeFormat = (value, decimals = 2) => {
                        if (value === null || value === undefined) return '-';
                        return Number(value).toFixed(decimals);
                    };
                    
                    modalContent.innerHTML = `
                        <h3>Resultados da Simulação: ${simId}</h3>
                        <p><strong>Moeda:</strong> ${details.operation_code || 'N/A'}</p>
                        <p><strong>Total de operações:</strong> ${trades.length}</p>
                        <p><strong>Lucro/Prejuízo:</strong> ${safeFormat(results.profit_loss)} (${safeFormat(results.profit_loss_percentage)}%)</p>
                        
                        <h4>Histórico de operações:</h4>
                        <div class="table-responsive">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>Tipo</th>
                                        <th>Preço</th>
                                        <th>Quantidade</th>
                                        <th>Valor Total</th>
                                        <th>Data/Hora</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${trades.map(trade => `
                                        <tr>
                                            <td><span class="badge badge-${trade.trade_type === 'BUY' ? 'success' : 'danger'}">${trade.trade_type}</span></td>
                                            <td>${safeFormat(trade.price)}</td>
                                            <td>${safeFormat(trade.quantity)}</td>
                                            <td>${safeFormat(trade.total_value)}</td>
                                            <td>${trade.timestamp || '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    // Exibir o modal
                    modal.style.display = 'block';
                    
                    // Fechar modal ao clicar no X
                    const closeBtn = modal.querySelector('.close');
                    if (closeBtn) {
                        closeBtn.addEventListener('click', function() {
                            modal.style.display = 'none';
                        });
                    }
                    
                    // Fechar modal ao clicar fora
                    window.addEventListener('click', function(event) {
                        if (event.target === modal) {
                            modal.style.display = 'none';
                        }
                    });
                } else {
                    showAlert('danger', `Erro: ${data.error || 'Falha ao obter resultados'}`);
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
            if (data.success) {
                showAlert('success', 'Simulação finalizada com sucesso!');
                
                // Remover da tabela
                const tbody = simulationTable.querySelector('tbody');
                const rows = tbody.querySelectorAll('tr');
                rows.forEach(row => {
                    const buttons = row.querySelectorAll('button');
                    for (let button of buttons) {
                        if (button.getAttribute('data-id') === simId) {
                            tbody.removeChild(row);
                            break;
                        }
                    }
                });
                
                // Mostrar os resultados finais
                showSimulationResults(simId);
            } else {
                showAlert('danger', `Erro: ${data.error || 'Falha ao parar simulação'}`);
            }
        })
        .catch(error => {
            console.error('Erro ao parar simulação:', error);
            showAlert('danger', 'Erro ao parar simulação. Verifique o console para mais detalhes.');
        });
    }

    // Função para carregar histórico de simulações
    function loadSimulationHistory() {
        const historyContainer = document.getElementById('simulation-history');
        if (!historyContainer) return;
        
        fetch('/api/simulation/history/list')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const simulations = data.simulations || [];
                    
                    if (simulations.length === 0) {
                        historyContainer.innerHTML = '<p>Nenhuma simulação encontrada.</p>';
                        return;
                    }
                    
                    let html = `
                        <div class="table-responsive">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Moeda</th>
                                        <th>Data</th>
                                        <th>Resultado</th>
                                        <th>Ações</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    simulations.forEach(sim => {
                        const isProfit = (sim.profit_loss && sim.profit_loss > 0);
                        const resultClass = isProfit ? 'success' : 'danger';
                        
                        html += `
                            <tr>
                                <td>${sim.id}</td>
                                <td>${sim.operation_code || 'N/A'}</td>
                                <td>${sim.created_at || 'N/A'}</td>
                                <td class="text-${resultClass}">${sim.profit_loss ? Number(sim.profit_loss).toFixed(2) : '0.00'} (${sim.profit_loss_percentage ? Number(sim.profit_loss_percentage).toFixed(2) : '0.00'}%)</td>
                                <td>
                                    <button class="button button-primary btn-view-sim" data-id="${sim.id}">Ver Detalhes</button>
                                </td>
                            </tr>
                        `;
                    });
                    
                    html += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    historyContainer.innerHTML = html;
                    
                    // Adicionar eventos aos botões
                    const viewButtons = document.querySelectorAll('.btn-view-sim');
                    viewButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const simId = this.getAttribute('data-id');
                            showSimulationResults(simId);
                        });
                    });
                } else {
                    historyContainer.innerHTML = `<p class="alert alert-danger">Erro ao carregar lista de simulações: ${data.error}</p>`;
                }
            })
            .catch(error => {
                console.error('Erro ao carregar histórico de simulações:', error);
                historyContainer.innerHTML = '<p class="alert alert-danger">Erro ao carregar lista de simulações</p>';
            });
    }

    // Função para carregar a carteira
    function loadWallet() {
        const walletTable = document.getElementById('wallet-table');
        const totalBalance = document.getElementById('total-balance');
        const walletUpdatedAt = document.getElementById('wallet-updated-at');
        
        if (!walletTable || !totalBalance) return;
        
        fetch('/api/wallet')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const balances = data.balances || [];
                    const tbody = walletTable.querySelector('tbody');
                    tbody.innerHTML = '';
                    
                    if (balances.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" class="text-center">Nenhum saldo encontrado</td></tr>';
                        totalBalance.textContent = '0.00 USDT';
                        return;
                    }
                    
                    let totalUsdt = 0;
                    
                    balances.forEach(balance => {
                        const row = document.createElement('tr');
                        
                        // Calcular total disponível (free + locked)
                        const total = (parseFloat(balance.free) || 0) + (parseFloat(balance.locked) || 0);
                        
                        // Verificar se temos um valor USDT
                        const usdtValue = balance.usdt_value || 0;
                        totalUsdt += parseFloat(usdtValue);
                        
                        row.innerHTML = `
                            <td>
                                <div class="d-flex align-items-center">
                                    <span class="coin-icon">${balance.asset?.slice(0, 1) || '?'}</span>
                                    ${balance.asset || 'Desconhecido'}
                                </div>
                            </td>
                            <td>${parseFloat(balance.free || 0).toFixed(8)}</td>
                            <td>${parseFloat(balance.locked || 0).toFixed(8)}</td>
                            <td>${total.toFixed(8)}</td>
                        `;
                        
                        tbody.appendChild(row);
                    });
                    
                    // Atualizar saldo total
                    totalBalance.textContent = `${totalUsdt.toFixed(2)} USDT`;
                    
                    // Atualizar timestamp
                    if (walletUpdatedAt) {
                        const now = new Date();
                        walletUpdatedAt.textContent = `Atualizado em: ${now.toLocaleTimeString()}`;
                    }
                } else {
                    const tbody = walletTable.querySelector('tbody');
                    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Erro: ${data.message || 'Falha ao carregar saldos'}</td></tr>`;
                    totalBalance.textContent = 'Erro';
                }
            })
            .catch(error => {
                console.error('Erro ao carregar carteira:', error);
                const tbody = walletTable.querySelector('tbody');
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Erro ao carregar saldos</td></tr>';
                totalBalance.textContent = 'Erro';
            });
    }

    // Exibir mensagem de alerta
    function showAlert(type, message) {
        if (!alerts) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert">&times;</button>
        `;
        
        alerts.appendChild(alert);
        
        // Auto-remover após 5 segundos
        setTimeout(() => {
            if (alert.parentNode === alerts) {
                alerts.removeChild(alert);
            }
        }, 5000);
        
        // Adicionar evento para fechar ao clicar
        alert.querySelector('.close').addEventListener('click', function() {
            if (alert.parentNode === alerts) {
                alerts.removeChild(alert);
            }
        });
    }

    // Exibir mensagem de erro de saldo insuficiente com estilo aprimorado
    function showInsufficientBalanceError(error) {
        // Criar o elemento de alerta
        const alertContainer = document.createElement('div');
        alertContainer.className = 'insufficient-balance-alert';
        
        // Determinar detalhes do erro
        let currency = error.currency || 'USDT';
        let available = error.available_balance ? error.available_balance.toFixed(8) : '0';
        let required = error.required_balance ? error.required_balance.toFixed(8) : '0';
        
        // Construir o conteúdo do alerta com estilo aprimorado
        alertContainer.innerHTML = `
            <div class="alert-header">
                <div class="alert-icon">
                    <span class="material-icons">warning</span>
                </div>
                <div class="alert-title">Saldo Insuficiente</div>
                <button class="alert-close">&times;</button>
            </div>
            <div class="alert-body">
                <p>Você não tem saldo suficiente para iniciar esta operação.</p>
                <div class="balance-details">
                    <div class="balance-row">
                        <div class="balance-label">Disponível:</div>
                        <div class="balance-value available">${available} ${currency}</div>
                    </div>
                    <div class="balance-row">
                        <div class="balance-label">Necessário:</div>
                        <div class="balance-value required">${required} ${currency}</div>
                    </div>
                    <div class="balance-row">
                        <div class="balance-label">Faltando:</div>
                        <div class="balance-value missing">${(required - available).toFixed(8)} ${currency}</div>
                    </div>
                </div>
                <div class="alert-actions">
                    <button class="button button-primary goto-wallet">Ver Carteira</button>
                </div>
            </div>
        `;
        
        // Adicionar estilo CSS inline para o alerta
        const style = document.createElement('style');
        style.textContent = `
            .insufficient-balance-alert {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 400px;
                background-color: var(--dark-secondary);
                border-radius: 8px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                z-index: 9999;
                border-left: 5px solid var(--danger);
            }
            
            .alert-header {
                display: flex;
                align-items: center;
                padding: 15px 20px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            
            .alert-icon {
                color: var(--danger);
                margin-right: 10px;
            }
            
            .alert-icon .material-icons {
                font-size: 24px;
            }
            
            .alert-title {
                font-size: 18px;
                font-weight: bold;
                flex-grow: 1;
            }
            
            .alert-close {
                background: none;
                border: none;
                color: var(--light-secondary);
                font-size: 24px;
                cursor: pointer;
                padding: 0;
            }
            
            .alert-body {
                padding: 20px;
            }
            
            .balance-details {
                background-color: rgba(0,0,0,0.2);
                border-radius: 6px;
                padding: 15px;
                margin: 15px 0;
            }
            
            .balance-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                padding-bottom: 8px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            
            .balance-row:last-child {
                margin-bottom: 0;
                padding-bottom: 0;
                border-bottom: none;
            }
            
            .balance-label {
                font-weight: 500;
                color: var(--light-secondary);
            }
            
            .balance-value {
                font-family: monospace;
                font-weight: bold;
            }
            
            .balance-value.available {
                color: var(--warning);
            }
            
            .balance-value.required {
                color: var(--primary);
            }
            
            .balance-value.missing {
                color: var(--danger);
            }
            
            .alert-actions {
                display: flex;
                justify-content: flex-end;
                margin-top: 20px;
            }
            
            .overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.6);
                z-index: 9998;
            }
        `;
        
        // Adicionar overlay
        const overlay = document.createElement('div');
        overlay.className = 'overlay';
        
        // Anexar elementos ao corpo do documento
        document.body.appendChild(style);
        document.body.appendChild(overlay);
        document.body.appendChild(alertContainer);
        
        // Configurar listeners de eventos
        alertContainer.querySelector('.alert-close').addEventListener('click', function() {
            document.body.removeChild(alertContainer);
            document.body.removeChild(overlay);
            document.body.removeChild(style);
        });
        
        overlay.addEventListener('click', function() {
            document.body.removeChild(alertContainer);
            document.body.removeChild(overlay);
            document.body.removeChild(style);
        });
        
        // Botão para ir para a carteira
        alertContainer.querySelector('.goto-wallet').addEventListener('click', function() {
            document.body.removeChild(alertContainer);
            document.body.removeChild(overlay);
            document.body.removeChild(style);
            
            // Redirecionar para a tab de wallet
            const dashboardTab = document.querySelector('.tab[data-target="tab-dashboard"]');
            if (dashboardTab) {
                dashboardTab.click();
            }
        });
    }

    // Inicialização de componentes específicos
    function initComponents() {
        // Inicializar formulário do bot
        if (botForm) {
            botForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = {
                    symbol: document.getElementById('bot-symbol').value,
                    operation_mode: document.getElementById('bot-operation-mode').value,
                    traded_quantity: parseFloat(document.getElementById('bot-quantity').value)
                };
                
                startBot(formData);
            });
        }
        
        // Inicializar formulário de simulação
        if (simulationForm) {
            simulationForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = {
                    stock_code: document.getElementById('sim-stock-code').value,
                    operation_code: document.getElementById('sim-operation-code').value,
                    quantity: parseFloat(document.getElementById('sim-quantity').value),
                    volatility_factor: parseFloat(document.getElementById('sim-volatility').value),
                    stop_loss: parseFloat(document.getElementById('sim-stop-loss').value),
                    acceptable_loss: parseFloat(document.getElementById('sim-acceptable-loss').value),
                    fallback_activated: document.getElementById('sim-fallback').checked
                };
                
                startSimulation(formData);
            });
        }
        
        // Inicializar atualização da carteira
        const refreshWalletBtn = document.getElementById('refresh-wallet');
        if (refreshWalletBtn) {
            refreshWalletBtn.addEventListener('click', loadWallet);
            // Carregar carteira inicialmente
            loadWallet();
        }
        
        // Inicializar histórico de simulações
        const simulationHistoryPage = document.getElementById('simulation-history');
        if (simulationHistoryPage) {
            loadSimulationHistory();
        }
    }

    // Layout responsivo para mobile
    function handleResponsiveLayout() {
        const isMobile = window.innerWidth < 768;
        const tables = document.querySelectorAll('table');
        
        if (isMobile) {
            tables.forEach(simplifyTableHeaders);
        } else {
            tables.forEach(restoreTableHeaders);
        }
    }

    // Simplificar cabeçalhos de tabela para mobile
    function simplifyTableHeaders(table) {
        if (!table.dataset.originalHeaders) {
            // Salvar cabeçalhos originais
            const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent);
            table.dataset.originalHeaders = JSON.stringify(headers);
            
            // Simplificar cabeçalhos
            table.querySelectorAll('th').forEach((th, index) => {
                if (index > 0 && index < headers.length - 1) {
                    th.setAttribute('data-original', th.textContent);
                    th.textContent = (index + 1).toString();
                }
            });
        }
    }

    // Restaurar cabeçalhos originais da tabela
    function restoreTableHeaders(table) {
        if (table.dataset.originalHeaders) {
            const headers = JSON.parse(table.dataset.originalHeaders);
            
            table.querySelectorAll('th').forEach((th, index) => {
                if (th.getAttribute('data-original')) {
                    th.textContent = th.getAttribute('data-original');
                }
            });
            
            // Limpar dataset
            delete table.dataset.originalHeaders;
        }
    }

    // Inicializar
    initComponents();
    handleResponsiveLayout();
    
    // Atualizar layout responsivo ao redimensionar
    window.addEventListener('resize', handleResponsiveLayout);
    
    // Buscar status inicial
    fetchStatus();
}); 