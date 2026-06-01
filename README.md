# 🎵 API de Extração de Áudio do YouTube

API Flask para extrair URLs de áudio de vídeos do YouTube usando apenas a ID do vídeo.

## 🚀 Deploy Rápido (Render.com)

### 1. Push para GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/seu-usuario/youtube-api.git
git push -u origin main
```

### 2. Deploy no Render

1. Acesse [render.com](https://render.com)
2. Faça login com GitHub
3. Clique em **New +** > **Blueprint**
4. Selecione seu repositório
5. Render detecta `render.yaml` automaticamente
6. Clique em **Apply**
7. Aguarde 3-5 minutos

Pronto! Sua API estará em: `https://seu-app.onrender.com`

📚 **Guia completo:** [DEPLOY_RENDER.md](DEPLOY_RENDER.md)

## 🎯 Endpoints

### POST /extract
Extrai URL de áudio de um vídeo.

**Request:**
```bash
curl -X POST https://seu-app.onrender.com/extract \
  -H "Content-Type: application/json" \
  -d '{"video_id": "dQw4w9WgXcQ"}'
```

**Response:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "audio_url": "https://...",
  "title": "Rick Astley - Never Gonna Give You Up",
  "duration": 212,
  "uploader": "Rick Astley",
  "cached": false
}
```

### GET /health
Verifica status da API.

```bash
curl https://seu-app.onrender.com/health
```

### GET /cache/stats
Estatísticas do cache.

```bash
curl https://seu-app.onrender.com/cache/stats
```

### POST /cache/clear
Limpa o cache.

```bash
curl -X POST https://seu-app.onrender.com/cache/clear
```

## 🔧 Funcionalidades

- ✅ **Cache inteligente** (4 horas) com SQLite
- ✅ **Rate limiting** (10 req/min configurável)
- ✅ **Validação de ID**
- ✅ **Logs estruturados**
- ✅ **Health check**
- ✅ **Tratamento de erros robusto**
- ✅ **Persistente** (cache sobrevive a reloads)
- ✅ **Suporte a cookies** (para vídeos com restrição de idade/login)
- ✅ **Sistema de fallback múltiplo** (4 configurações diferentes para máxima compatibilidade)

## 📦 Arquivos do Projeto

```
.
├── app_flask.py         # Aplicação Flask principal
├── cache_sqlite.py      # Implementação cache SQLite (fallback)
├── requirements.txt     # Dependências Python
├── Procfile            # Comando para Render
├── runtime.txt         # Versão do Python
├── render.yaml         # Configuração Render (Blueprint)
├── .gitignore          # Arquivos ignorados
├── README.md           # Este arquivo
└── DEPLOY_RENDER.md    # Guia completo de deploy
```

## 🛠️ Desenvolvimento Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar servidor
python app_flask.py

# Testar
curl -X POST http://localhost:5000/extract \
  -H "Content-Type: application/json" \
  -d '{"video_id": "dQw4w9WgXcQ"}'
```

## 🍪 Configuração de Cookies (Opcional)

Para acessar vídeos com restrição de idade ou que exigem login, você pode usar cookies do YouTube:

### 1. Exportar Cookies do Navegador

**Opção A: Extensão do Chrome/Firefox**
1. Instale a extensão [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Acesse [youtube.com](https://youtube.com) e faça login
3. Clique na extensão e exporte os cookies
4. Salve como `youtube_cookies.txt` na raiz do projeto

**Opção B: Usando yt-dlp**
```bash
yt-dlp --cookies-from-browser chrome --cookies youtube_cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 2. Configurar a API

O arquivo `youtube_cookies.txt` já está configurado para ser usado automaticamente. A API detecta o arquivo e usa os cookies quando disponível.

**Verificar se está funcionando:**
```bash
# Inicie a API e veja os logs
python app_flask.py

# Você verá: "Usando arquivo de cookies: youtube_cookies.txt"
```

### 3. Deploy no Render com Cookies

Para usar cookies no Render.com:

1. **Adicione o arquivo ao repositório:**
   ```bash
   git add youtube_cookies.txt
   git commit -m "Add YouTube cookies"
   git push
   ```

2. **Ou use variável de ambiente** (mais seguro):
   - No dashboard do Render, vá em **Environment**
   - Adicione: `YOUTUBE_COOKIES_FILE=/etc/secrets/youtube_cookies.txt`
   - Use o Render Secret Files para fazer upload do arquivo

⚠️ **Importante:** Cookies expiram! Atualize-os periodicamente (geralmente a cada 6 meses).

## ⚙️ Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DEBUG` | `False` | Modo debug |
| `YOUTUBE_COOKIES_FILE` | `youtube_cookies.txt` | Caminho do arquivo de cookies |
| `CACHE_TYPE` | `sqlite` | Tipo de cache (sqlite, memory) |
| `CACHE_TTL` | `14400` | TTL do cache em segundos (4h) |
| `CACHE_DB_PATH` | `cache.db` | Caminho do arquivo SQLite |
| `RATE_LIMIT_REQUESTS` | `10` | Requisições por minuto |
| `MAX_VIDEO_ID_LENGTH` | `20` | Tamanho máximo da ID |

## 🐛 Troubleshooting

### Deploy falhou no Render

1. Verifique os logs no dashboard do Render
2. Certifique-se que todos os arquivos estão no repositório
3. Verifique se `render.yaml` está na raiz do projeto

### yt-dlp não funciona

O YouTube muda frequentemente sua API. Atualize:

```bash
pip install --upgrade yt-dlp
```

No Render, isso acontece automaticamente a cada deploy.

### Erro "Requested format is not available"

A API agora usa **sistema de fallback múltiplo** que tenta 4 configurações diferentes:
1. `web_embedded` (melhor para servidores)
2. `android` (mais confiável)
3. `ios` (alternativa)
4. `default` (última tentativa)

Veja os logs para saber qual configuração funcionou:
```
INFO - Tentando configuração: web_embedded
INFO - ✅ Sucesso com configuração: web_embedded
```

Se todas falharem, considere adicionar cookies (veja seção de Cookies).

📚 **Guia completo:** [RENDER_FIX.md](RENDER_FIX.md)

### Cache não funciona

O Render usa SQLite automaticamente. Verifique:
1. Logs mostram: `✅ Cache SQLite inicializado com sucesso`?
2. Teste endpoint: `/cache/stats`
3. Veja se o caminho do arquivo está correto

## 📊 Por que Render.com com SQLite?

| Feature | Render + SQLite | Outras Opções |
|---------|-----------------|---------------|
| **YouTube** | ✅ Funciona | ⚠️ Algumas bloqueiam |
| **Cache** | ✅ SQLite persistente | ⚠️ Redis pago ou memória |
| **Deploy** | ✅ Git automático | ⚠️ Manual em algumas |
| **SSL** | ✅ Incluído | ✅ Maioria inclui |
| **Custo** | ✅ 100% Grátis | ⚠️ Redis pode custar |
| **Configuração** | ✅ Zero (via render.yaml) | ⚠️ Pode ser complexo |

## 📝 Licença

MIT
