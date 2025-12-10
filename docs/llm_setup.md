# LLM Kurulum Rehberi

Bu belge Fortress Director’ın varsayılan modellerini indirmek ve Ollama ortamını hazırlamak için gereken adımları özetler. Amaç, projeyi ilk kez kuran birinin tek kaynaktan ilerleyebilmesidir.

## 1. Gereksinimler

- [Ollama](https://ollama.com/download) 0.1.45+ sürümü
- En az 15 GB boş disk alanı (modeller sıkıştırılmış hâlde tutulur)
- İnternet erişimi (modeller yalnızca ilk seferde indirilir)

## 2. Modeller ve Agent Eşlemesi

| Agent / Kullanım                     | Varsayılan Model | Not |
|--------------------------------------|------------------|-----|
| Director, Planner, Judge             | `qwen2:1.5b`     | Karar kalitesi için düşük sıcaklık ayarları kullanılır. |
| World Renderer, Event, World Agents  | `phi3:mini`      | Atmosfer/narratif üretimi için hızlı ve hafif. |
| Creativity / Character deneysel akışı| `gemma:2b`       | Opsiyonel; yaratıcı varyasyonlar için kullanılır. |
| Genel fallback / deneme              | `mistral:latest` | Doküman boyunca referans verilen baseline model. |

`fortress_director/settings.py` içindeki `SETTINGS.models` sözlüğü bu isimlerle uyumludur; yeni model çektiyseniz `settings.yaml` veya env override yoluyla değiştirebilirsiniz.

## 3. Modelleri Otomatik İndirme

Depodaki `scripts/download_models.sh` tüm zorunlu modelleri sırayla çeker:

```bash
chmod +x scripts/download_models.sh
./scripts/download_models.sh
```

Script şu komutları çalıştırır:

```bash
ollama pull mistral:latest
ollama pull qwen2:1.5b
ollama pull phi3:mini
```

Gerekirse ek olarak `ollama pull gemma:2b` komutu ile creativity/character akışında kullanılan modeli indirebilirsiniz.

## 4. Ollama Kurulumu Kısa Özet

1. Ollama’yı indirin ve yükleyin.
2. Servisin çalıştığını doğrulamak için `ollama list` komutunu çalıştırın.
3. Yukarıdaki indirme script’ini veya komutları çalıştırın.
4. `settings.yaml` içinde `models` bloğunu kullanarak farklı isimler vermediyseniz ek bir ayar gerekmez.

## 5. Sorun Giderme

- `ollama pull` sırasında bağlantı hatası alırsanız komutu tekrar çalıştırabilirsiniz; kısmen indirilmiş dosyalar tamamlanır.
- Model isimleri `settings.yaml` veya `FORTRESS_MODEL_VARIANTS` env değişkeni ile değiştirildiğinde, aynı adı Ollama’dan çektiğinizden emin olun.
- Alternatif sunucu/port kullanıyorsanız `settings.py` içindeki `ollama_base_url` değerini override edin veya `.env` dosyasında `OLLAMA_HOST`’u set edin.

Kurulum bittiğinde `python -m scripts.dev_tools check_llm` komutu her agent için “OK” mesajı döndürmelidir. Aksi durumda Ollama servisinin çalıştığını ve ilgili modellerin listede olduğunu doğrulayın.
