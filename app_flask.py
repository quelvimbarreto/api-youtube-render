import os
import re
import json
import logging
from functools import wraps
from datetime import timedelta
from flask import Flask, request, jsonify
import yt_dlp

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS - permite requisições de clientes Dart/web de qualquer origem
@app.after_request
def add_cors_headers(response):
    """Adiciona headers CORS para permitir requisições de clientes Dart/web."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.before_request
def log_request():
    """Loga detalhes de toda requisição recebida para debug."""
    body = request.get_data(as_text=True)[:200] if request.data else ''
    logger.info(
        f"→ {request.method} {request.path} | "
        f"Content-Type: {request.content_type} | "
        f"User-Agent: {request.user_agent} | "
        f"Body: {body}"
    )


# Configurações via variáveis de ambiente
app.config.update(
    MAX_VIDEO_ID_LENGTH=int(os.getenv('MAX_VIDEO_ID_LENGTH', 20)),
    SUPPORTED_DOMAINS=os.getenv('SUPPORTED_DOMAINS', 'youtube.com,youtu.be').split(','),
    TIMEOUT=int(os.getenv('TIMEOUT', 30)),
    RATE_LIMIT_REQUESTS=int(os.getenv('RATE_LIMIT_REQUESTS', 10)),
    CACHE_TTL=int(os.getenv('CACHE_TTL', 14400)),  # 4 horas em segundos
    REDIS_URL=os.getenv('REDIS_URL', None),
    CACHE_TYPE=os.getenv('CACHE_TYPE', 'auto'),  # auto, redis, sqlite, memory
)

# Configuração do cache
cache_backend = None
cache_type = 'memory'

# Tenta Redis primeiro (se configurado)
if app.config['CACHE_TYPE'] in ['auto', 'redis'] and app.config['REDIS_URL']:
    try:
        import redis
        cache_backend = redis.from_url(
            app.config['REDIS_URL'],
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        cache_backend.ping()
        cache_type = 'redis'
        logger.info("✅ Cache Redis conectado com sucesso")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao conectar Redis: {e}")
        cache_backend = None

# Se Redis falhou, tenta SQLite
if cache_backend is None and app.config['CACHE_TYPE'] in ['auto', 'sqlite']:
    try:
        from cache_sqlite import SQLiteCache
        cache_backend = SQLiteCache(
            db_path=os.getenv('CACHE_DB_PATH', 'cache.db'),
            ttl=app.config['CACHE_TTL']
        )
        if cache_backend.ping():
            cache_type = 'sqlite'
            logger.info("✅ Cache SQLite inicializado com sucesso")
        else:
            cache_backend = None
    except Exception as e:
        logger.warning(f"⚠️ Erro ao inicializar SQLite: {e}")
        cache_backend = None

# Fallback para memória
if cache_backend is None:
    cache_type = 'memory'
    logger.info("ℹ️ Usando cache em memória (fallback)")

# Cache em memória como fallback
memory_cache = {}


def validate_video_id(video_id: str) -> bool:
    """Valida se a ID do vídeo tem formato válido."""
    if not video_id or not isinstance(video_id, str):
        return False
    if len(video_id) > app.config['MAX_VIDEO_ID_LENGTH']:
        return False
    # IDs do YouTube são alfanuméricos com - e _
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, video_id))


def extract_video_id(url_or_id: str) -> str:
    """Extrai a ID do vídeo de uma URL ou retorna a ID se já for uma."""
    if not url_or_id:
        return None
    
    # Se já é uma ID válida, retorna direto
    if validate_video_id(url_or_id):
        return url_or_id
    
    # Tenta extrair de URL
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{10,}).*',  # youtu.be/ID ou youtube.com/watch?v=ID
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{10,})',  # embed
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{10,})',  # shorts
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


def get_cache(key: str):
    """Obtém valor do cache (Redis, SQLite ou memória)."""
    try:
        if cache_type == 'redis':
            value = cache_backend.get(key)
            if value:
                return json.loads(value)
        elif cache_type == 'sqlite':
            return cache_backend.get(key)
        else:
            # Cache em memória com expiração
            from time import time
            if key in memory_cache:
                data, expiry = memory_cache[key]
                if time() < expiry:
                    return data
                else:
                    del memory_cache[key]
    except Exception as e:
        logger.error(f"Erro ao ler cache: {e}")
    return None


def set_cache(key: str, value: dict, ttl: int = None):
    """Define valor no cache (Redis, SQLite ou memória)."""
    if ttl is None:
        ttl = app.config['CACHE_TTL']
    
    try:
        if cache_type == 'redis':
            cache_backend.setex(key, ttl, json.dumps(value))
        elif cache_type == 'sqlite':
            cache_backend.set(key, value, ttl)
        else:
            # Cache em memória com expiração
            from time import time
            memory_cache[key] = (value, time() + ttl)
    except Exception as e:
        logger.error(f"Erro ao salvar cache: {e}")


def clear_expired_memory_cache():
    """Limpa entradas expiradas do cache em memória."""
    from time import time
    now = time()
    expired_keys = [k for k, (_, expiry) in memory_cache.items() if now >= expiry]
    for key in expired_keys:
        del memory_cache[key]


def rate_limit(f):
    """Decorator simples para rate limiting (baseado em memória)."""
    from collections import deque
    from time import time
    
    if not hasattr(f, 'requests'):
        f.requests = deque()
    
    now = time()
    # Limpa requisições antigas
    while f.requests and now - f.requests[0] > 60:
        f.requests.popleft()
    
    if len(f.requests) >= app.config['RATE_LIMIT_REQUESTS']:
        return jsonify({'error': 'Rate limit excedido. Tente novamente em breve.'}), 429
    
    f.requests.append(now)
    return None


@app.route('/extract', methods=['POST'])
def extract():
    """Extrai URL de áudio a partir da ID do vídeo."""
    # Rate limiting
    rate_check = rate_limit(extract)
    if rate_check:
        return rate_check
    
    try:
        # Tenta obter JSON, mas aceita outros formatos
        data = None
        if request.is_json:
            data = request.get_json()
        elif request.data:
            # Tenta parsear como JSON mesmo sem Content-Type correto
            try:
                data = request.get_json(force=True)
            except Exception:
                pass
        
        if not data:
            return jsonify({'error': 'Corpo da requisição deve ser JSON ou video_id'}), 400
        
        video_id = data.get('video_id')
        if not video_id:
            return jsonify({'error': 'video_id é obrigatório'}), 400
        
        # Validação da ID
        if not validate_video_id(video_id):
            return jsonify({'error': 'ID de vídeo inválida'}), 400
        
        # Verifica cache
        cache_key = f"video:{video_id}"
        cached_result = get_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit para video_id: {video_id}")
            cached_result['cached'] = True
            return jsonify(cached_result)
        
        logger.info(f"Cache miss para video_id: {video_id}")
        
        # Constrói URL do YouTube
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        
        # Extrai áudio
        result = extract_audio_url(video_url)
        if 'error' in result:
            return jsonify(result), 404
        
        # Prepara resposta
        response_data = {
            'video_id': video_id,
            'audio_url': result['audio_url'],
            'title': result.get('title'),
            'duration': result.get('duration'),
            'uploader': result.get('uploader'),
            'cached': False
        }
        
        # Salva no cache
        set_cache(cache_key, response_data)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f'Erro ao extrair áudio: {str(e)}')
        return jsonify({'error': 'Erro interno no servidor'}), 500


def extract_audio_url(video_url: str) -> dict:
    """Extrai URL de áudio de um vídeo do YouTube com múltiplos fallbacks."""
    # Caminho do arquivo de cookies
    cookies_file = os.getenv('YOUTUBE_COOKIES_FILE', 'youtube_cookies.txt')
    
    # Verifica se o arquivo de cookies existe
    cookies_exists = os.path.exists(cookies_file)
    cookies_to_use = None
    
    if cookies_exists:
        logger.info(f"Arquivo de cookies encontrado: {cookies_file}")
        
        # Se o arquivo está em /etc/secrets (read-only no Render), copia para /tmp
        if cookies_file.startswith('/etc/secrets/'):
            try:
                import shutil
                temp_cookies = '/tmp/youtube_cookies.txt'
                shutil.copy2(cookies_file, temp_cookies)
                cookies_to_use = temp_cookies
                logger.info(f"Cookies copiados para: {temp_cookies}")
            except Exception as e:
                logger.warning(f"Erro ao copiar cookies: {e}. Tentando sem cookies.")
                cookies_to_use = None
        else:
            cookies_to_use = cookies_file
    else:
        logger.warning(f"Arquivo de cookies não encontrado: {cookies_file}")
        
    # Configuração android + process=False (funcionou nos testes)
    # process=False evita o erro "Requested format is not available"
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
            }
        },
        'cookiefile': cookies_to_use,
    }

    result = _try_extract_with_config(video_url, ydl_opts)
    if result and 'audio_url' in result:
        return result

    # Fallback: tenta sem cookies (cookies expirados podem causar falha em alguns vídeos)
    logger.info("ℹ️ Tentando sem cookies como fallback")
    ydl_opts_no_cookies = {**ydl_opts, 'cookiefile': None}
    result = _try_extract_with_config(video_url, ydl_opts_no_cookies)
    if result and 'audio_url' in result:
        return result

    logger.error(f"Falha ao extrair áudio")
    return {'error': 'Não foi possível extrair o áudio. Tente novamente mais tarde.'}


def _try_extract_with_config(video_url: str, ydl_opts: dict) -> dict:
    """Tenta extrair áudio com uma configuração específica."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # process=False é CRÍTICO: evita o erro "Requested format is not available"
            # ao retornar TODOS os formatos crus sem tentar selecionar um
            logger.info(f"ℹ️ Extraindo com process=False para evitar erro de formato")
            info = ydl.extract_info(video_url, download=False, process=False)
            
            # Tenta obter URL direta de diferentes formas
            audio_url = None
            
            # Método 1: URL direta no info
            if 'url' in info and info['url']:
                audio_url = info['url']
            
            # Método 2: Procura nos formatos disponíveis
            elif 'formats' in info and info['formats']:
                # Procura por formato de áudio
                for fmt in info['formats']:
                    # Prioriza formatos apenas de áudio
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        audio_url = fmt.get('url')
                        if audio_url:
                            break
                
                # Se não encontrou áudio puro, pega qualquer formato com áudio
                if not audio_url:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('url'):
                            audio_url = fmt['url']
                            break
            
            # Método 3: Tenta requested_formats
            elif 'requested_formats' in info and info['requested_formats']:
                for fmt in info['requested_formats']:
                    if fmt.get('acodec') != 'none':
                        audio_url = fmt.get('url')
                        if audio_url:
                            break
            
            if not audio_url:
                return None
            
            # Valida se a URL é válida
            if not audio_url.startswith('http'):
                return None
            
            return {
                'audio_url': audio_url,
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f'Erro ao baixar informações do vídeo: {error_msg}')
        
        if 'Video unavailable' in error_msg:
            return {'error': 'Vídeo não disponível'}
        elif 'Sign in' in error_msg or 'login' in error_msg.lower():
            return {'error': 'YouTube está bloqueando acesso. Tente novamente em alguns minutos ou use cookies de autenticação.'}
        elif 'player response' in error_msg.lower():
            return {'error': 'Erro ao processar vídeo. Tente atualizar o yt-dlp: pip install --upgrade yt-dlp'}
        elif 'proxy' in error_msg.lower() or 'tunnel' in error_msg.lower():
            return {'error': 'Erro de conexão. O servidor pode estar bloqueando acesso ao YouTube.'}
        
        raise  # Re-raise para tentar próxima configuração
        
    except Exception as e:
        logger.error(f'Erro inesperado: {str(e)}')
        raise  # Re-raise para tentar próxima configuração


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check."""
    cache_size = len(memory_cache) if cache_type == 'memory' else 'N/A'
    
    # Tenta obter versão do yt-dlp
    try:
        import yt_dlp
        ytdlp_version = yt_dlp.version.__version__
    except Exception:
        ytdlp_version = 'unknown'
    
    return jsonify({
        'status': 'healthy',
        'cache_backend': cache_type,
        'cache_size': cache_size,
        'yt_dlp_version': ytdlp_version
    })


@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Limpa o cache (útil para debug)."""
    try:
        if cache_type == 'redis':
            # Limpa apenas chaves que começam com "video:"
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = cache_backend.scan(cursor, match='video:*', count=100)
                if keys:
                    deleted += cache_backend.delete(*keys)
                if cursor == 0:
                    break
            return jsonify({'message': f'{deleted} entradas removidas do cache Redis'})
        elif cache_type == 'sqlite':
            deleted = cache_backend.clear()
            return jsonify({'message': f'{deleted} entradas removidas do cache SQLite'})
        else:
            count = len(memory_cache)
            memory_cache.clear()
            return jsonify({'message': f'{count} entradas removidas do cache em memória'})
    except Exception as e:
        logger.error(f'Erro ao limpar cache: {e}')
        return jsonify({'error': 'Erro ao limpar cache'}), 500


@app.route('/cache/stats', methods=['GET'])
def cache_stats():
    """Retorna estatísticas do cache."""
    try:
        if cache_type == 'redis':
            # Conta chaves que começam com "video:"
            cursor = 0
            count = 0
            while True:
                cursor, keys = cache_backend.scan(cursor, match='video:*', count=100)
                count += len(keys)
                if cursor == 0:
                    break
            
            info = cache_backend.info('memory')
            return jsonify({
                'backend': 'redis',
                'cached_videos': count,
                'memory_used': info.get('used_memory_human', 'N/A'),
                'ttl_seconds': app.config['CACHE_TTL']
            })
        elif cache_type == 'sqlite':
            stats = cache_backend.stats()
            # Limpa expirados antes de mostrar stats
            expired = cache_backend.clear_expired()
            return jsonify({
                'backend': 'sqlite',
                'cached_videos': stats.get('valid_entries', 0),
                'expired_entries': stats.get('expired_entries', 0),
                'db_size_mb': stats.get('db_size_mb', 0),
                'ttl_seconds': app.config['CACHE_TTL'],
                'expired_cleaned': expired
            })
        else:
            clear_expired_memory_cache()
            return jsonify({
                'backend': 'memory',
                'cached_videos': len(memory_cache),
                'ttl_seconds': app.config['CACHE_TTL']
            })
    except Exception as e:
        logger.error(f'Erro ao obter estatísticas: {e}')
        return jsonify({'error': 'Erro ao obter estatísticas'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handler para 404 que mostra as rotas disponíveis para debug."""
    routes = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        routes.append(f"{rule.rule} [{methods}]")

    logger.warning(f"❌ 404 - Rota não encontrada: {request.method} {request.path}")
    logger.warning(f"📋 Rotas registradas: {routes}")

    return jsonify({
        'error': 'Rota não encontrada',
        'path': request.path,
        'method': request.method,
        'available_routes': routes
    }), 404


# Handler para OPTIONS (CORS preflight para navegadores)
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Retorna 200 para preflight CORS em qualquer rota."""
    return jsonify({}), 200


# Log das rotas registradas na inicialização (roda também sob gunicorn)
logger.info("🚀 Rotas registradas:")
for rule in app.url_map.iter_rules():
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    logger.info(f"   {rule.rule} [{methods}]")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    logger.info(f"✅ Servidor iniciando em 0.0.0.0:{port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
