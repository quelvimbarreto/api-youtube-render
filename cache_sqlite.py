import sqlite3
import json
import time
import logging
from threading import Lock
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLiteCache:
    """Cache usando SQLite - funciona em qualquer hospedagem."""
    
    def __init__(self, db_path='cache.db', ttl=14400):
        """
        Inicializa o cache SQLite.
        
        Args:
            db_path: Caminho para o arquivo do banco
            ttl: Time to live em segundos (padrão: 4 horas)
        """
        self.db_path = db_path
        self.ttl = ttl
        self.lock = Lock()
        self._init_db()
    
    def _init_db(self):
        """Cria a tabela de cache se não existir."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            ''')
            # Índice para melhorar performance de limpeza
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires 
                ON cache(expires_at)
            ''')
            conn.commit()
            conn.close()
    
    def get(self, key):
        """Obtém valor do cache."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT value, expires_at FROM cache WHERE key = ?',
                    (key,)
                )
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    value, expires_at = result
                    if time.time() < expires_at:
                        return json.loads(value)
                    else:
                        # Expirado, remove
                        self.delete(key)
                
                return None
        except Exception as e:
            logger.error(f"Erro ao ler cache: {e}")
            return None
    
    def set(self, key, value, ttl=None):
        """Define valor no cache."""
        if ttl is None:
            ttl = self.ttl
        
        try:
            expires_at = time.time() + ttl
            value_json = json.dumps(value)
            
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO cache (key, value, expires_at)
                    VALUES (?, ?, ?)
                ''', (key, value_json, expires_at))
                
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")
    
    def delete(self, key):
        """Remove valor do cache."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao deletar cache: {e}")
    
    def clear(self):
        """Limpa todo o cache."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache')
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                return deleted
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return 0
    
    def clear_expired(self):
        """Remove entradas expiradas."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM cache WHERE expires_at < ?',
                    (time.time(),)
                )
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                return deleted
        except Exception as e:
            logger.error(f"Erro ao limpar expirados: {e}")
            return 0
    
    def stats(self):
        """Retorna estatísticas do cache."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Total de entradas
                cursor.execute('SELECT COUNT(*) FROM cache')
                total = cursor.fetchone()[0]
                
                # Entradas válidas (não expiradas)
                cursor.execute(
                    'SELECT COUNT(*) FROM cache WHERE expires_at > ?',
                    (time.time(),)
                )
                valid = cursor.fetchone()[0]
                
                # Tamanho do arquivo
                db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                
                conn.close()
                
                return {
                    'total_entries': total,
                    'valid_entries': valid,
                    'expired_entries': total - valid,
                    'db_size_bytes': db_size,
                    'db_size_mb': round(db_size / 1024 / 1024, 2)
                }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
    
    def ping(self):
        """Testa conexão com o banco."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
            return True
        except Exception:
            return False
