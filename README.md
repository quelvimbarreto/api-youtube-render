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

## ⚙️ Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DEBUG` | `False` | Modo debug |
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
