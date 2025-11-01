import logging
import random
from fortress_director.orchestrator.orchestrator import Orchestrator
from pathlib import Path

# Log ayarları
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "demo_run.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("demo")


def run_demo_turns(turn_count=10):
    orch = Orchestrator.build_default()
    # State'i sıfırla
    orch.state_store.persist(orch.state_store._fresh_default())
    logger.info("Demo başlatıldı: State sıfırlandı.")
    all_turns = []
    for turn in range(1, turn_count + 1):
        try:
            result = orch.run_turn()
            logger.info(f"Turn {turn} başlatıldı.")
            # Seçeneklerden random seçim yap
            options = result.get("options", [])
            if options:
                choice = random.choice(options)
                logger.info(f"Turn {turn} random seçim: {choice}")
                result = orch.run_turn(player_choice_id=choice.get("id"))
            else:
                logger.info(f"Turn {turn} - Seçenek yok, oyun bitmiş olabilir.")
            all_turns.append(result)
            logger.info(
                f"Turn {turn} tamamlandı. State: {result.get('WORLD_CONTEXT', {})}"
            )
        except Exception as e:
            logger.warning(f"Turn {turn} hata ile atlandı: {e}")
            continue
    # Final
    final_state = orch.state_store.snapshot()
    logger.info("Demo tamamlandı. Final state:")
    logger.info(final_state)
    print("Demo tamamlandı. Sonuçlar log dosyasına kaydedildi: logs/demo_run.log")
    return all_turns, final_state


if __name__ == "__main__":
    run_demo_turns(10)
