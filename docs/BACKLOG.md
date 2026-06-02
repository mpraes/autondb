📑 AutonDB - Product Backlog
Status do Projeto: 🚀 Inicialização do MVP

Foco do MVP: Migração ultra-rápida de bancos pequenos/médios (Postgres, MySQL, SQLite) com validação prévia de dados (Pre-Flight Sanitizer) usando IA.

🏗️ Epic 1: Fundação do Core & Arquitetura (CLI)
Foco em criar a estrutura de código open source, contratos de banco de dados e execução via terminal.

[ X ]  STORY-1.1: Estrutura Base do Projeto

Criar a árvore de diretórios do Python (src/engine, src/databases, src/services) e configurar o ambiente virtual (venv ou poetry).

[ X ] STORY-1.2: Interface de Conexão (IDatabase)

Implementar a classe abstrata/interface mãe que padroniza os métodos connect(), get_schema(), stream_data() e bulk_insert().

[ X ] STORY-1.3: Conector SQLite

Implementar a classe SQLiteDB usando aiosqlite para leitura e escrita assíncrona.

[ X ] STORY-1.4: Conector PostgreSQL

Implementar a classe PostgresDB usando asyncpg, focando no método de alta performance copy_to_table ou inserts em lote.

[ X ] STORY-1.5: Conector MySQL

Implementar a classe MySQLDB usando aiomysql para escrita otimizada em lote.

🧠 Epic 2: Cérebro do AutonDB (Mapeamento & IA)
Integrar a OpenAI API para analisar a estrutura do banco e prever erros sem tocar nos dados sensíveis.

[ X ] STORY-2.1: Cliente de IA (AIService)

Criar a classe que inicializa clientes de múltiplos provedores de IA (OpenAI, Groq, OpenRouter, Anthropic Claude, Synthetic, etc) utilizando as API Keys informadas pelo usuário por variáveis de ambiente (.env), com suporte dinâmico para trocar providers em runtime.

[ X ] STORY-2.2: Engenharia de Prompt (Smart Schema Mapping)

Escrever e testar o prompt que recebe o DDL de origem (ex: SQLite) e retorna um JSON estruturado com o mapeamento exato de tipos para o destino (ex: Postgres).

[ X ] STORY-2.3: Pre-Flight Sanitizer (Validador de Dados Sujos)

Criar rotina que lê uma amostragem estatística das colunas (ex: primeiras 1000 linhas) e envia metadados para a IA detectar se há dados textuais incompatíveis com o destino (ex: letras em campos de data).

🏎️ Epic 3: Motor de Execução & KPIs (O Orquestrador)
Fazer a mágica acontecer: ler de um lado, transformar com as regras da IA e descarregar no outro na velocidade máxima.

[ X ] STORY-3.1: Classe MigrationEngine

Desenvolver o orquestrador principal que recebe a aprovação do mapeamento da IA e inicia o pipeline assíncrono.

[ X ] STORY-3.2: Desativação Provisória de Constraints

Adicionar travas no motor para desativar Foreign Keys e Índices no banco de destino antes do streaming começar, e reativá-los ao final (essencial para velocidade).

[ X ] STORY-3.3: Módulo KPITracker

Implementar o contador em tempo real que calcula: linhas processadas, MB/segundo e tempo estimado restante (ETA).

[ X ] STORY-3.4: Auditoria de Integridade (O Seguro do DBA)

Criar uma rotina pós-migração que roda um COUNT e validação rápida por tabela para garantir correspondência exata de 100% entre origem e destino.

💻 Epic 4: Distribuição & Interface Desktop (Tauri)
Trazer o poder do terminal para uma interface visual de clique, leve e sem atrito de instalação.

[ ] STORY-4.1: Setup do Projeto Tauri

Andaimar o frontend com Tauri na raiz do projeto (gerando os diretórios src-tauri).

[ ] STORY-4.2: Empacotamento do Core Python

Configurar o PyInstaller para congelar o core do AutonDB em um binário nativo isolado.

[ ] STORY-4.3: Tela de Configuração (Zero Atrito)

Criar interface limpa para colar as strings de conexão dos bancos e a chave da OpenAI.

[ ] STORY-4.4: Tela de Preview da IA

Exibir de forma visual o mapeamento sugerido pela IA para que o usuário possa clicar em "Aprovar e Iniciar Migração".

[ ] STORY-4.5: Painel de Controle (Foguete)

Criar a tela de progresso com os velocímetros de linhas/segundo calculados pelo KPITracker e botão de download do PDF de Auditoria.