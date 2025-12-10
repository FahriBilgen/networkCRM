# Utility Functions

Utility kategorisi, sistem etiketleri, bayraklar ve metrik düzeltmeleri gibi yardımcı operasyonları içerir. Bu fonksiyonlar diğer kategorilerin etkilerini tamamlayan meta-işlemler sağlar.

Örnek fonksiyonlar:

- `adjust_metric(metric:str, delta:int, cause:str?)` — Herhangi bir metrik üzerinde kontrollü değişim yapar.
- `log_message(message:str, severity:str?)` — Turn günlüğüne özel kayıt ekler.
- `tag_state(tag:str)` — Durum üzerine işaret bırakarak diğer ajanlara sinyal verir.
- `set_flag(flag:str)` / `clear_flag(flag:str)` — Küresel durum bayraklarını yönetir.

Utility fonksiyonları genellikle `metrics`, `flags` ve `log` alanlarına etki eder ve düşük gaz maliyetiyle çağrılabilir.
