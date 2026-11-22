# Jellyfin-refina 🎬✨

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern_Async-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Port](https://img.shields.io/badge/Port-8585-indigo.svg)](#regras-de-rede-e-portas)

**Jellyfin-refina** é uma aplicação web completa desenvolvida em Python (FastAPI + SQLite + Tailwind Dark Mode) projetada para catalogação rápida, auditoria de integridade do acervo (duplicatas, saúde de legendas para Bazarr, arquivos de baixa resolução) e curadoria inteligente com inteligência artificial generativa (Google Gemini) e TMDB, além de integração direta com trailers oficiais no YouTube.

> **Desenvolvido por Nelson Cherubim de Andrade**

---

## 📋 Sumário
1. [Regras de Rede e Portas](#-regras-de-rede-e-portas)
2. [Premissa de Diretórios e Mapeamento](#-premissa-de-diretórios-e-mapeamento)
3. [Principais Recursos](#-principais-recursos)
4. [Stack Tecnológica](#-stack-tecnológica)
5. [Estrutura do Projeto](#-estrutura-do-projeto)
6. [Como Subir com Docker Compose](#-como-subir-com-docker-compose)
7. [Deploy em Produção via Portainer Stack](#-deploy-em-produção-via-portainer-stack)
8. [Versionamento no GitHub Privado](#-versionamento-no-github-privado)
9. [Segurança Implementada](#-segurança-implementada)

---

## 🌐 Regras de Rede e Portas

A aplicação foi rigorosamente configurada para operar na porta **8585** (`PORT=8585`). 

O sistema possui uma trava de segurança em código que impede explicitamente o uso das seguintes portas já alocadas pelo ecossistema multimídia do host:
`80, 81, 443, 3000, 5055, 6767, 7878, 8096, 8191, 8989, 9000, 9091, 9696 e 51413`.

---

## 📁 Premissa de Diretórios e Mapeamento

O **Jellyfin-refina** adota uma convenção simples e direta para o mapeamento de volumes no Docker Compose, sem depender de variáveis de ambiente para definir caminhos no host:

- **Estrutura Padrão do Servidor**:
  - Caminho no Host: `/jellynux/media`
  - Caminho no Contêiner: `/media`
- **Subpastas Recomendadas**:
  - `/jellynux/media/filmes` &rarr; no contêiner: `/media/filmes`
  - `/jellynux/media/series` &rarr; no contêiner: `/media/series`
  - `/jellynux/media/shows` &rarr; no contêiner: `/media/shows`

> [!NOTE]
> **Utiliza outro diretório no seu servidor?**
> Caso sua coleção de mídia esteja em outro ponto de montagem (por exemplo, `/mnt/storage/media` ou `/media`), basta ajustar a linha de volume no `docker-compose.yml`:
> ```yaml
> volumes:
>   - ./data:/app/data
>   - /SEU/CAMINHO/DE/MIDIA:/media
> ```
> O **Explorador de Diretórios do Servidor** (botão "Procurar") abre automaticamente por padrão em `/media`, fazendo com que suas pastas de filmes, séries e shows apareçam imediatamente para seleção com um clique.

---

## 🚀 Principais Recursos

- **Fluxo de Autenticação Seguro**:
  - **Setup Inicial**: No primeiro acesso, quando não há usuários no banco, apresenta exclusivamente a tela de criação do administrador.
  - **Bloqueio de Registro**: Assim que o administrador é criado, a tela de setup é bloqueada e passa a exibir apenas a tela de Login tradicional.
  - Senhas criptografadas com `bcrypt` (12 rounds) e cookies de sessão seguros (`HttpOnly`, `SameSite=Lax`).
- **Navegador Visual de Diretórios no Servidor**:
  - Modal interativo ("Procurar") para navegar e selecionar pastas montadas no Docker (`/media/filmes`, `/media/series`, `/media/shows`, etc.) sem necessidade de digitação manual e sem fazer upload de arquivos.
  - Proteção avançada contra Path Traversal (`os.path.realpath`, sanitização de caracteres e validação de permissões).
- **Scanner Inteligente de Mídias**:
  - Varre recursivamente arquivos `.mp4`, `.mkv`, `.avi`, `.mov`, `.m4v`, `.webm`.
  - Regex avançada para limpeza automática de tags de release (`1080p`, `4K`, `BluRay`, `WEB-DL`, `x264`, `x265`, `HDR`, grupos como `YIFY`, `RARBG`, etc.), extraindo título limpo e ano.
  - Detecção automática de legendas `.srt` associadas na mesma pasta.
  - Agrupamento de séries por temporada e episódio (`S01E02`).
- **Página de Detalhes com Metadados Ricos & YouTube**:
  - Pôster em alta definição, notas, gêneros e elenco principal (via TMDB).
  - Curiosidades de bastidores e resenhas geradas por IA (via Google Gemini).
  - **Botão Obrigatório "Watch Trailer"**: Link direto e de destaque para o trailer oficial da obra no YouTube.
  - Cache no SQLite com botão "Atualizar Dados".
  - Fallback 100% funcional caso o servidor esteja sem internet ou sem chaves de API externas.
- **Auditor de Acervo (Saúde da Biblioteca)**:
  - Espaço total em disco (em GB/TB).
  - Detector de arquivos duplicados no acervo.
  - Detector de itens sem legenda `.srt` (com link direto de filtro para facilitar automação no Bazarr).
  - Alerta de mídias em baixa resolução (&lt;720p / SD) para upgrade de qualidade.
- **Curadoria IA ("O Que Assistir Hoje?")**:
  - Assistente inteligente que analisa os títulos do catálogo local com base no humor do usuário (ex: "Quero rir", "Ação eletrizante", "Suspense tenso") e sugere o filme ou série ideal com justificativa de curadoria.
- **Gerenciador de API Keys na Interface**:
  - Tela `/settings` para cadastrar, editar e testar conexão com `GEMINI_API_KEY` e `TMDB_API_KEY`.

---

## 🛠️ Stack Tecnológica

- **Backend**: Python 3.11, FastAPI, Uvicorn, SQLAlchemy, Bcrypt, HTTPX, ItsDangerous.
- **Banco de Dados**: SQLite persistente (`/app/data/jellyfin_refina.db`).
- **Frontend**: HTML5, Tailwind CSS (via CDN), Font Awesome 6, JavaScript assíncrono.
- **Container**: Imagem Docker otimizada baseada em `python:3.11-slim`, com usuário não-root `appuser` (UID 10001) e `HEALTHCHECK` interno.

---

## 📁 Estrutura do Projeto

```
jelly-refina-app/
├── app/
│   ├── config.py                 # Configurações e proteção de portas
│   ├── database.py               # Conexão SQLite / SQLAlchemy
│   ├── models.py                 # Modelos ORM (User, MediaItem, Setting)
│   ├── schemas.py                # Validação Pydantic
│   ├── auth.py                   # Criptografia Bcrypt e cookies de sessão
│   ├── scanner.py                # Parser de nomes, regex de títulos e detecção de legendas
│   ├── metadata_service.py       # Integração TMDB, Gemini, YouTube Trailer e Fallbacks
│   ├── main.py                   # Ponto de entrada FastAPI
│   ├── routes/
│   │   ├── auth_routes.py        # Setup inicial, Login e Logout
│   │   ├── dashboard_routes.py   # Dashboard e Auditor de Saúde
│   │   ├── directories_routes.py # Configuração de pastas e API segura do explorador de arquivos
│   │   ├── media_routes.py       # Catálogos (Filmes, Séries, Shows) e Detalhes
│   │   ├── ai_routes.py          # "O que assistir hoje?" com IA
│   │   └── settings_routes.py    # Gerenciamento de chaves de API
│   ├── static/
│   │   ├── css/custom.css        # Tema escuro elegante Jellyfin
│   │   └── js/app.js             # Funções de busca instantânea e modal do explorador
│   └── templates/
│       ├── base.html             # Layout com navbar e rodapé Nelson Cherubim de Andrade
│       ├── setup.html            # Primeiro acesso (apenas criação de admin)
│       ├── login.html            # Tela de autenticação
│       ├── dashboard.html        # Visão geral e Auditor de Acervo
│       ├── directories.html      # Diretórios, modal Procurar e scanner
│       ├── media_list.html       # Catálogo com filtros de resolução, SRT e busca instantânea
│       ├── media_detail.html     # Detalhes, poster, Watch Trailer e IA
│       ├── recommendations.html  # "O que assistir hoje?"
│       └── settings.html         # Configurações de API Keys
├── data/                         # Volume do banco SQLite persistente
├── Dockerfile                    # Multi-stage, non-root user, porta 8585, HEALTHCHECK
├── docker-compose.yml            # Mapeamento 8585:8585 e volumes
├── requirements.txt              # Dependências Python
├── .env.example                  # Variáveis de ambiente de exemplo
├── .gitignore                    # Bloqueio rigoroso de segredos e bases locais
├── .dockerignore                 # Otimização de build do container
└── README.md                     # Documentação completa
```

---

## 🐳 Como Subir com Docker Compose

### 1. Clonar e preparar o ambiente
```bash
cp .env.example .env
# Edite o .env se desejar informar as chaves antecipadamente
```
### Observação: ⚠️ Permissões da Pasta de Dados (Obrigatório antes de iniciar)

Por segurança, o contêiner executa a aplicação internamente com um usuário restrito sem privilégios de `root` (**UID/GID `10001`**). Se o Docker criar a pasta `./data` automaticamente, ela pertencerá ao `root` e impedirá a criação do banco de dados SQLite (`unable to open database file`).

Antes de subir o contêiner pela primeira vez, crie a pasta e ajuste a propriedade na raiz do projeto:

```bash
mkdir -p data && chown -R 10001:10001 data
```

> **Dica:** Caso não esteja operando como `root`, utilize `sudo chown -R 10001:10001 data`. Se os seus diretórios de mídia no servidor tiverem permissões restritas, garanta também que o usuário `10001` possua permissão de leitura nas pastas mapeadas em `/media`.


### 2. Construir e iniciar o container
```bash
docker compose up -d --build
```

### 3. Acessar a aplicação
Abra no seu navegador:
👉 **`http://localhost:8585`**

---

## 📦 Deploy em Produção via Portainer Stack

Para subir no seu Portainer existente sem conflito com os outros serviços multimídia:

1. Acesse o **Portainer** &rarr; selecione seu Environment (Local).
2. Vá em **Stacks** &rarr; clique em **Add Stack**.
3. Nomeie a stack como: `jellyfin-refina`.
4. Cole o conteúdo abaixo no editor Web:

```yaml
version: '3.8'

services:
  jellyfin-refina:
    image: jellyfin-refina:latest
    container_name: jellyfin-refina
    restart: unless-stopped
    ports:
      - "8585:8585"
    environment:
      - PORT=8585
      - SECRET_KEY=gere_uma_chave_segura_aqui
      - DATA_DIR=/app/data
      - GEMINI_API_KEY=
      - TMDB_API_KEY=
    volumes:
      - ./data:/app/data
      # Volume padrão mapeado (ajuste /jellynux/media caso use outro diretório no host):
      - /jellynux/media:/media
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8585/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

5. Clique em **Deploy the stack**.
6. Acesse via `http://IP-DO-SEU-SERVIDOR:8585`.

---

## 🔒 Versionamento no GitHub Privado

O repositório já está 100% blindado contra vazamento acidental de credenciais e bancos de dados através dos arquivos `.gitignore` e `.dockerignore`.

Para enviar para um repositório privado no GitHub:

```bash
# 1. Iniciar o repositório git local (se ainda não iniciado)
git init
git add .
git commit -m "feat: initial commit Jellyfin-refina production ready"

# 2. Criar o repositório privado no GitHub e conectar o remote
git remote add origin git@github.com:SEU_USUARIO/jellyfin-refina.git
git branch -M main
git push -u origin main
```

> **Garantia de Segurança**: O `.gitignore` garante que arquivos `.env`, bases de dados `.db`/`.sqlite`, logs e vídeos nunca serão enviados para o GitHub.

---

## 🛡️ Segurança Implementada

1. **Path Traversal Protection**: O explorador de diretórios do servidor (`/api/fs/browse`) valida os caminhos canônicos utilizando `Path.resolve()`, impedindo que usuários maliciosos acessem arquivos fora das pastas permitidas.
2. **Non-Root Docker User**: O container executa sob o usuário `appuser` (UID 10001), minimizando vetores de escalonamento de privilégios no host Docker.
3. **Senhas Fortes com Bcrypt**: Hashes gerados com 12 salt rounds.
4. **Proteção de Sessão**: Cookies assinados criptograficamente com flags `HttpOnly` e `SameSite=Lax`.
5. **Prevenção de Colisão de Portas**: Validação nativa que impede a inicialização nas portas reservadas do ecossistema multimídia.
   
