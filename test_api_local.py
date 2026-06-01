#!/usr/bin/env python3
"""
Teste rápido da função extract_audio_url.
"""
import os
import sys

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

from app_flask import extract_audio_url

def test():
    """Testa a extração de áudio."""
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("="*60)
    print("🧪 TESTE DA FUNÇÃO extract_audio_url")
    print("="*60)
    print(f"🎥 URL: {video_url}")
    print("\n⏳ Extraindo...")
    
    result = extract_audio_url(video_url)
    
    print("\n" + "="*60)
    if 'error' in result:
        print(f"❌ ERRO: {result['error']}")
        return False
    else:
        print("✅ SUCESSO!")
        print(f"📝 Título: {result.get('title')}")
        print(f"👤 Canal: {result.get('uploader')}")
        print(f"⏱️  Duração: {result.get('duration')} segundos")
        print(f"🔗 URL: {result.get('audio_url')[:80]}...")
        return True

if __name__ == '__main__':
    success = test()
    print("="*60)
    sys.exit(0 if success else 1)
