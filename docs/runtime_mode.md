# Runtime Mode Rehberi

Fortress Director iki modda çalışabilir:

- **LLM modu (`FORTRESS_LLM_MODE=llm`)**: Tüm agent’lar Ollama üzerinden gerçek modelleri çağırır.
- **Stub modu (`FORTRESS_LLM_MODE=stub`)**: Güvenli fallback’ler çalışır, ağ erişimi gerekmez.

## Çalışma Şekilleri

1. **.env dosyası veya ortam değişkeni**

   ```bash
   # .env veya shell
   export FORTRESS_LLM_MODE=stub
   ```

   Uygulama başlarken `llm/runtime_mode.py` bu değeri okuyarak global modu belirler.

2. **CLI üzerinden geçiş**

   ```bash
   python -m scripts.dev_tools llm_summary --limit 20
   python -m scripts.dev_tools benchmark --runs 5 --no-llm
   ```

   `scripts.dev_tools` komutları `set_llm_enabled()` fonksiyonunu kullanarak modu runtime’da değiştirir.

3. **HTTP API**

   `/api/status/llm_mode` endpoint’ine `{"use_llm": true/false}` göndermek aynı globali günceller. UI da bu endpoint’i kullanır; Atmosphere paneli anlık olarak güncellenir.

## Testler

`FORTRESS_RUN_LLM_TESTS=1` olduğunda `tests/integration/test_llm_pipeline.py` gibi gerçek LLM kullanan testler çalışır. Varsayılan `.env.example` değeri `0`’dır; CI’da testler stub modda kalır.

## Sorun Giderme

- Uygulama her tekrar başlatıldığında `.env` değerleri okunur. Runtime’da API ile moda geçiş yaptıysanız ama yeniden başlattığınızda eski moda dönüyorsa `.env`’i senkronize ettiğinizden emin olun.
- UI halen stub modda görünüyor ise `/api/status` yanıtındaki `mode` alanını kontrol edin; gerekirse `scripts.dev_tools check_llm` ile modelleri doğrulayın.
