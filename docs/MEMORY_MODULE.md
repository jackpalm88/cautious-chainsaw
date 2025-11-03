# Memory modulis

## Kopsavilkums
Memory modulis nodrošina trīsslāņu atmiņas arhitektūru tirdzniecības aģentam, apvienojot īstermiņa kontekstu, vēsturisko lēmumu datus un agregētu paraugu sniegumu. Moduļa publiskā API tiek eksponēta caur `Memory` pakotni (`from Memory import ...`) un pašlaik izmanto SQLite datubāzi kā noturības slāni.

| Slānis | Apraksts | Galvenās klases | Fiziska tabula |
| --- | --- | --- | --- |
| MI (Market Intelligence) | Īstermiņa konteksts, kas tiek padots LLM balstītiem aģentiem. | [`MemorySnapshot`](../src/Memory/models.py) | Aprēķināts no citām tabulām |
| LLR (Low-level Reflection) | Pilns lēmuma ieraksts ar tirgus kontekstu. | [`StoredDecision`](../src/Memory/models.py) | `decisions` |
| HLR (High-level Reflection) | Agregētu paraugu snieguma metriku glabātuve. | [`Pattern`](../src/Memory/models.py) | `patterns` |
| Atgriezeniskā saite | Slēgto darījumu rezultāti, kas sasaista lēmumus ar iznākumiem. | [`TradeOutcome`](../src/Memory/models.py) | `outcomes` |

## Pakotnes struktūra
```
src/Memory/
├── __init__.py          # Publiskā API un dokumentācijas kopsavilkums
├── models.py            # Dataklases, kas reprezentē atmiņā glabātos resursus
└── storage/
    ├── __init__.py      # Glabātuves moduļu eksports
    ├── base.py          # `MemoryStore` protokols un `StorageError`
    └── sqlite_store.py  # Noklusētā SQLite implementācija
```

## Dataklases un to lauki
### StoredDecision
- Identifikatori: `id`, `timestamp`, `symbol`
- Lēmuma atribūti: `action`, `confidence`, `lots`, `stop_loss`, `take_profit`
- Tirgus konteksts: `price`, `rsi`, `macd`, `bb_position`, `regime`
- Aģentu izvades (JSON): `signal_agent_output`, `risk_agent_output`, `context_agent_output`, `synthesis_agent_output`

### TradeOutcome
- Atsauce uz lēmumu caur `decision_id`
- Slēgšanas metadati: `closed_at`, `result`, `pips`, `duration_minutes`, `exit_reason`
- Papildu cenas: `fill_price`, `exit_price`

### Pattern
- Identitāte un definīcija: `pattern_id`, `rsi_min`, `rsi_max`, `macd_signal`, `bb_position`, `regime`
- Snieguma metriku kopsavilkums: `win_rate`, `avg_pips`, `sample_size`, `last_updated`

### MemorySnapshot
- MI slāņa redzamība: `recent_decisions`, `current_regime`
- Veiktspējas rādītāji 30 dienu griezumā: `win_rate_30d`, `avg_win_pips`, `avg_loss_pips`, `total_trades_30d`
- Atrastie paraugi: `similar_patterns`
- Pievienota `to_summary(max_tokens=500)` metode, lai ģenerētu teksta izvilkumu LLM promptiem.

## Glabātuves līgums (`Memory.storage.base`)
`MemoryStore` protokols apraksta visas operācijas, kurām jābūt pieejamām jebkurai glabātuves implementācijai:
- `save_decision(...)`, `load_decision(...)`, `load_recent_decisions(...)`
- `save_outcome(...)`, `load_outcomes(...)`, `get_outcome(...)`
- `load_snapshot(...)` – sagatavo MI slāņa kopsavilkumu
- `save_pattern(...)`, `load_patterns(...)`, `find_similar_patterns(...)`
- Palīgoperācijas: `get_statistics(...)`, `health_check()`, `clear_old_data(...)`

Kļūdu stāvokļi tiek ietverti ar `StorageError` izņēmumu, ko jāizmanto arī pielāgotām backend implementācijām.

## SQLiteMemoryStore īstenojums
- Datubāzes inicializācija: konstruktors pieņem `db_path` (pēc noklusējuma `memory.db`), nodrošina direktoriju esamību un izveido shēmu, ja tā neeksistē.
- Shēma sastāv no trim tabulām ar indeksiem biežāk lietotajiem vaicājumiem (`timestamp`, `symbol`, `result`, `sample_size`).
- Visi datumi tiek glabāti ISO 8601 formātā (`datetime.isoformat()`), kas ļauj droši rekonstruēt Python `datetime` objektus.
- Ierakstu rakstīšanai izmantota `INSERT OR REPLACE`, lai atjauninātu lēmumus pēc identifikatora.
- JSON lauki tiek serializēti ar `json.dumps`, un `None` vērtības netiek glabātas (SQLite `NULL`).
- `load_snapshot(...)` apkopo pēdējo N dienu datus, aprēķinot:
  - kopējo darījumu skaitu un uzvaru īpatsvaru,
  - vidējo pips ieguvumu/zaudējumu,
  - pēdējos lēmumus un līdzīgus paraugus (izmantojot `find_similar_patterns`).
- Retences apstrādei pieejama `clear_old_data(days=365)` metode, kas dzēš lēmumus, iznākumus un paraugus ārpus norādītā loga.

## Izmantošanas piemērs
```python
from Memory import SQLiteMemoryStore, StoredDecision, TradeOutcome
from datetime import datetime

store = SQLiteMemoryStore("./data/memory.db")

store.save_decision(
    StoredDecision(
        id="EURUSD-2024-01-15T10:00:00Z",
        timestamp=datetime.utcnow(),
        symbol="EURUSD",
        action="BUY",
        confidence=0.78,
        lots=0.5,
        price=1.0865,
    )
)

store.save_outcome(
    TradeOutcome(
        decision_id="EURUSD-2024-01-15T10:00:00Z",
        closed_at=datetime.utcnow(),
        result="WIN",
        pips=24.3,
        duration_minutes=180,
        exit_reason="TP",
    )
)

snapshot = store.load_snapshot(days=30)
print(snapshot.to_summary())
```

## Testēšana
- `tests/test_memory_smoke.py` nodrošina dūmu testu, kas izveido pagaidu SQLite datubāzi, saglabā lēmumu un iznākumu un pārbauda, vai 30 dienu kopsavilkumā ir vismaz viens darījums.
- Papildu vienības testi saglabāti zem `src/trading_agent/memory/tests/` un validē modeļu serializāciju un glabātuves darbības.

## Paplašināšana un labākā prakse
- Izveidojot jaunu glabātuves backend, realizē `MemoryStore` protokola metodes un atkārto esošo izņēmumu ķēdi (`raise StorageError(...) from exc`).
- Atjaunini dokumentāciju un dūmu testu, ja maini shēmu vai pievieno jaunas tabulas.
- Izmanto `MemorySnapshot.to_summary()` kā vienīgo veidu, kā ģenerēt īstermiņa kontekstu LLM agentiem, lai saglabātu konsekvenci starp slāņiem.

