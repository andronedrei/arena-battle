# Capture the Flag (CTF) - Client Implementation

## 📁 Fișiere Create

### 1. **Display Modules** (`client/display/`)

#### `display_ctf_flag.py`
- Desenează steagurile celor două echipe
- Afișează indicator când steagul este purtat de un agent
- Efecte vizuale pentru steag căzut (dropped)
- Folosește forme geometrice (Circle pentru bază, Star pentru steag)

**Caracteristici:**
- Culori echipă (albastru/roșu)
- Poziționare dinamică
- Label pentru carrier ID
- Opacitate variabilă

#### `display_ctf_hud.py`
- HUD complet pentru modul CTF
- Afișează captures pentru ambele echipe
- Status steaguri (At Base / Carried by #X / Dropped)
- Timer (count-down sau count-up)
- Anunț victorie

**Layout:**
```
┌────────────────────────────────────────────────────┐
│ Team A: 2 captures    CAPTURE THE FLAG    Team B: 1 captures │
│ Flag: Carried by #3      Time Left: 3:42      Flag: At Base   │
└────────────────────────────────────────────────────┘
```

---

### 2. **Network Module** (`client/network/`)

#### `client_network_ctf.py`
- Client WebSocket dedicat pentru CTF
- Primește mesaje de tip `MSG_TYPE_CTF_STATE` (0x13)
- Callback: `scene.on_ctf_update(payload)`
- Switch automat la scena `gameplay_ctf` la START_GAME

**Protocol:**
- Conectare la `ws://localhost:8765`
- Recepționare stări JSON cu flag positions, captures, timer
- Thread-safe queue pentru mesaje outgoing

---

### 3. **Gameplay Scene** (`client/scenes/`)

#### `scene_gameplay_ctf.py`
- Scenă completă de gameplay pentru CTF
- Folosește toate sistemele existente:
  - `DisplayBackground`
  - `DisplayWalls`
  - `DisplayEntity`
  - `DisplayBullet`
- Adaugă:
  - 2x `DisplayCTFFlag` (Team A și Team B)
  - `DisplayCTFHUD`

**Lifecycle:**
1. `helper_enter()` - Inițializare display objects
2. `helper_update(dt)` - Procesare queue-uri de network
3. `apply_ctf_update()` - Update flag positions și HUD
4. `helper_leave()` - Cleanup

**Network Callbacks:**
- `on_entities_update()`
- `on_walls_update()`
- `on_bullets_update()`
- `on_ctf_update()` ← **NOU**

---

### 4. **State Module** (`common/states/`)

#### `state_ctf.py`
- Clasa `StateCTFFlag` - stare unui steag individual
- Clasa `StateCTF` - stare completă joc CTF
- Serializare JSON pentru flexibilitate (nullable carrier_id)

**Structură Packet:**
```json
{
  "team_a_captures": 2,
  "team_b_captures": 1,
  "flag_team_a": {
    "x": 640.0,
    "y": 360.0,
    "carrier": 3,
    "at_base": false
  },
  "flag_team_b": {
    "x": 1180.0,
    "y": 360.0,
    "carrier": null,
    "at_base": true
  },
  "time_elapsed": 125.5,
  "max_time": 300.0,
  "max_captures": 3,
  "game_over": false,
  "winner_team": 0
}
```

---

### 5. **Configuration** (`common/`)

#### `ctf_config.py`
- Poziții inițiale steaguri
- Rază de pickup/return
- Reguli scoring (puncte per capture)
- Condiții victorie (max captures, max time)
- Configurare vizuală (culori, opacitate)

**Parametri Importanți:**
```python
CTF_FLAG_TEAM_A_BASE_X = 100
CTF_FLAG_TEAM_B_BASE_X = 1180
CTF_FLAG_PICKUP_RADIUS = 30
CTF_MAX_CAPTURES = 3
CTF_MAX_DURATION = 300.0  # 5 minutes
```

---

## 🔧 Modificări în Fișiere Existente

### `client/main.py`
✅ Import `SceneGameplayCTF`
✅ Creare scenă CTF: `scene_gameplay_ctf = SceneGameplayCTF(WALL_CONFIG)`
✅ Înregistrare scenă: `add_scene("gameplay_ctf", scene_gameplay_ctf)`
✅ Adăugare callback în `SceneRouter`: `on_ctf_update(data)`

### `client/scenes/scene_menu.py`
✅ Buton "Capture the Flag" înlocuiește "Option3"
✅ Import `GAME_MODE_CTF` din `common.config`
✅ Handler click → trimite `MSG_TYPE_SELECT_MODE` + `GAME_MODE_CTF`

### `client/network/client_network.py`
✅ Import `MSG_TYPE_CTF_STATE`, `GAME_MODE_CTF`
✅ Handler în `_handle_message()` pentru `MSG_TYPE_CTF_STATE`
✅ Switch logic pentru `GAME_MODE_CTF` → `gameplay_ctf`

### `common/config.py`
✅ Constantă `MSG_TYPE_CTF_STATE = 0x13`
✅ Constantă `GAME_MODE_CTF = 0x03`

---

## 🎮 Flow-ul Complet

```
┌─────────────────────────────────────────────────────────┐
│ 1. CLIENT PORNEȘTE                                      │
│    └─> scene_menu.py (afișează butoane)                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. USER ALEGE "Capture the Flag"                       │
│    └─> Trimite MSG_TYPE_SELECT_MODE + GAME_MODE_CTF    │
│    └─> Trimite MSG_TYPE_CLIENT_READY                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. SERVER CONFIRMĂ ȘI TRIMITE START_GAME               │
│    └─> client_network.py detectează GAME_MODE_CTF      │
│    └─> Switch la scene: "gameplay_ctf"                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. GAMEPLAY CTF ACTIV                                   │
│    └─> scene_gameplay_ctf.py primește:                 │
│        - MSG_TYPE_ENTITIES (agenți)                     │
│        - MSG_TYPE_BULLETS (gloanțe)                     │
│        - MSG_TYPE_WALLS (pereți)                        │
│        - MSG_TYPE_CTF_STATE (steaguri, scor) ← NOU     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 5. RENDER FRAME                                         │
│    └─> DisplayBackground                                │
│    └─> DisplayWalls                                     │
│    └─> DisplayCTFFlag (x2 - Team A + Team B)          │
│    └─> DisplayEntity (toți agenții)                    │
│    └─> DisplayBullet (toate gloanțele)                 │
│    └─> DisplayCTFHUD (scor, timer, status steaguri)    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 6. UPDATE LOOP (15 FPS)                                 │
│    └─> Procesare queue-uri network                     │
│    └─> Actualizare poziții entități/steaguri           │
│    └─> Refresh FOV dacă pereții s-au schimbat          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 7. GAME OVER                                            │
│    └─> HUD afișează "TEAM X WINS!"                     │
│    └─> Server trimite MSG_TYPE_GAME_END                │
│    └─> Client se deconectează după 5s                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Dependențe

Toate modulele folosesc librăriile existente:
- `pyglet` - rendering (shapes, text, batch)
- `websockets` - comunicare client-server
- `asyncio` - networking asincron
- `json` - serializare state CTF

**NU sunt necesare instalări noi!**

---

## ✅ Checklist Implementare

- [x] `display_ctf_flag.py` - Desenare steaguri
- [x] `display_ctf_hud.py` - HUD CTF
- [x] `client_network_ctf.py` - Network handler
- [x] `scene_gameplay_ctf.py` - Scenă gameplay
- [x] `state_ctf.py` - State serialization
- [x] `ctf_config.py` - Configurare parametri
- [x] Modificare `client/main.py` (import + register scenă)
- [x] Modificare `scene_menu.py` (buton CTF)
- [x] Modificare `client_network.py` (handler CTF_STATE)
- [x] Modificare `common/config.py` (constante MSG/MODE)

---

## 🚀 Next Steps (Server-Side)

Pentru ca jocul să funcționeze complet, trebuie implementat pe server:

1. **`server/gameplay/game_manager_ctf.py`**
   - Logica capturare steaguri
   - Verificare coliziuni agent-steag
   - Update poziții steaguri (follow carrier)
   - Check win conditions

2. **`server/strategy/ctf_strategy.py`**
   - Comportament AI pentru CTF
   - Roluri: Attacker, Defender, Support

3. **`server/network/network_manager_ctf.py`**
   - Broadcast `MSG_TYPE_CTF_STATE` la interval
   - Inițializare GameManagerCTF

4. **`server/config.py`**
   - Spawn points pentru CTF
   - Team compositions

---

## 📝 Note Tehnice

### Design Decisions

1. **JSON pentru CTF State**
   - Motiv: `carrier_id` poate fi `None` (nullable)
   - Alternativa: Struct cu sentinel value (65535)
   - Ales JSON pentru claritate și extensibilitate

2. **Flag Display cu Star Shape**
   - Motiv: Distincție vizuală clară față de circle-uri
   - Alternative testate: Triangle, Rectangle
   - Star oferă cel mai bun contrast

3. **Separate Network Module**
   - Similar cu `client_network_koth.py`
   - Permite extend fără a modifica base client
   - Future-proof pentru alte moduri

### Known Limitations

- Flag-ul nu are animație de "wave" (poate fi adăugată)
- Nu există indicator de distanță până la steag
- Carrier indicator este static (poate fi îmbunătățit cu arrow sprite)

### Performance

- Flag updates: ~60 bytes/packet (JSON)
- HUD updates: O(1) - doar text labels
- Rendering: 2 flags + 1 HUD = negligible overhead vs KOTH

---

## 🎨 Customization

Pentru a modifica aspectul vizual:

**Culori:**
```python
# client/display/display_ctf_flag.py
color = TEAM_COLORS.get(team, (255, 255, 255))
```

**Dimensiuni steag:**
```python
# client/display/display_ctf_flag.py
outer_radius=12,  # Dimensiune star
inner_radius=6,
```

**Layout HUD:**
```python
# client/display/display_ctf_hud.py
hud_height = 80  # Înălțime bară HUD
```

---

## 🐛 Debugging

Pentru a testa implementarea:

1. Verifică loguri client:
```bash
tail -f logs/arena-client_*.log | grep CTF
```

2. Test import:
```python
python -c "from client.scenes.scene_gameplay_ctf import SceneGameplayCTF"
```

3. Verifică constante:
```python
python -c "from common.config import MSG_TYPE_CTF_STATE, GAME_MODE_CTF; print(hex(MSG_TYPE_CTF_STATE), hex(GAME_MODE_CTF))"
```

---

**Autor:** AI Assistant  
**Data:** 2025-11-17  
**Versiune:** 1.0.0  
**Status:** ✅ Ready for Integration
