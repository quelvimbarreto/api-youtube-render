#!/usr/bin/env python3
"""
Script de teste para verificar diferentes configurações de extração do yt-dlp.
"""
import os
import yt_dlp

def test_extraction_config(config_name, ydl_opts, video_url):
    """Testa uma configuração específica do yt-dlp."""
    print(f"\n{'='*60}")
    print(f"🧪 Testando: {config_name}")
    print(f"{'='*60}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("⏳ Extraindo informações...")
            info = ydl.extract_info(video_url, download=False)
            
            audio_url = info.get('url')
            if audio_url:
                print(f"✅ SUCESSO!")
                print(f"📝 Título: {info.get('title')}")
                print(f"👤 Canal: {info.get('uploader')}")
                print(f"⏱️  Duração: {info.get('duration')} segundos")
                print(f"🔗 URL: {audio_url[:80]}...")
                return True
            else:
                print(f"❌ FALHOU: URL de áudio não encontrada")
                return False
                
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        return False


def main():
    """Testa diferentes configurações."""
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    cookies_file = 'youtube_cookies.txt'
    cookies_exists = os.path.exists(cookies_file)
    
    print("="*60)
    print("🎯 TESTE DE EXTRAÇÃO DO YOUTUBE")
    print("="*60)
    print(f"🎥 Vídeo: {video_url}")
    print(f"🍪 Cookies: {'✅ Encontrado' if cookies_exists else '❌ Não encontrado'}")
    
    # Configuração 1: Android client (mais confiável)
    config1 = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cookiefile': cookies_file if cookies_exists else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
            }
        },
    }
    
    # Configuração 2: iOS client
    config2 = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cookiefile': cookies_file if cookies_exists else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],
            }
        },
    }
    
    # Configuração 3: Android + iOS (fallback)
    config3 = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cookiefile': cookies_file if cookies_exists else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
            }
        },
    }
    
    # Configuração 4: Sem extractor_args (padrão do yt-dlp)
    config4 = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cookiefile': cookies_file if cookies_exists else None,
    }
    
    results = []
    results.append(("Android Client", test_extraction_config("Android Client", config1, video_url)))
    results.append(("iOS Client", test_extraction_config("iOS Client", config2, video_url)))
    results.append(("Android + iOS", test_extraction_config("Android + iOS (Atual)", config3, video_url)))
    results.append(("Padrão yt-dlp", test_extraction_config("Padrão yt-dlp", config4, video_url)))
    
    # Resumo
    print(f"\n{'='*60}")
    print("📊 RESUMO DOS TESTES")
    print(f"{'='*60}")
    for name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{name:25} {status}")
    
    print(f"\n{'='*60}")
    successful = sum(1 for _, success in results if success)
    print(f"✅ {successful}/{len(results)} configurações funcionaram")
    print(f"{'='*60}")
    
    if successful > 0:
        print("\n💡 Recomendação: Use a primeira configuração que funcionou")
    else:
        print("\n⚠️ Nenhuma configuração funcionou. Possíveis causas:")
        print("   1. Cookies expirados - exporte novos cookies")
        print("   2. yt-dlp desatualizado - execute: pip install --upgrade yt-dlp")
        print("   3. YouTube bloqueando acesso - tente novamente mais tarde")


if __name__ == '__main__':
    main()
