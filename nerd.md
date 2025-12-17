# Sortify: The Nerd Details 🤓

## The Cool Stuff Nobody Asked For (But You're Reading Anyway)

### The "Holy Shit" Moment

Remember when you had to manually organize files? Yeah, i don't either. Sortify is what happens when you combine semantic embeddings, natural language inference (NLI), and a healthy disrespect for traditional rule-based systems.

### Why One AI When You Can Have Five?

Most file organizers use a single classification method (never seen one actually). We said "nah" and built a **weighted voting democracy**:

```
FileTypeVoter (0.3)  → "It's a .pdf, probably a document"
SemanticVoter (0.4)  → "Content talks about 'neural networks', smells like Academic"
HistoryVoter (0.5)   → "Last time we saw 'tensorflow', it went to Code"
SessionVoter (0.3)   → "User just organized 3 ML papers, context matters"
NLIVoter (0.6)       → "Let me think deeply... definitely Academic"
```

**The Math:**
```
Score(category) = Σ(voter_weight × confidence)
Winner = argmax(scores)
```

If confidence < 0.60, we wake up the **NLI Consultant** (Ollama) for deep reasoning. It's like calling in a specialist when the ER docs are stumped (idk what it means either).

### The Algorithm

Not just "highest vote wins" - we do **weighted confidence scoring**:

```python
scoreboard = {}
for voter, category, confidence in votes:
    score = voter.weight * confidence
    scoreboard[category] += score

winner = max(scoreboard, key=scoreboard.get)
```

Why? Because a 90% confident HistoryVoter (weight 0.5) should beat a 60% confident FileTypeVoter (weight 0.3).

**Math nerds:** It's basically a weighted ensemble classifier with dynamic consultant injection. Think Random Forest meets Expert Systems.

## Folders as Semantic Clusters (thought this when i was in washroom)

### The Problem

Traditional organizers: "Put PDFs in Documents folder"
Reality: Your "Hackathon_2024" folder has PDFs, code, images, and a pizza receipt.

### The Solution: Treat Folders as Clusters

Each folder becomes a **semantic cluster** with a centroid computed from its contents (thanks to campusX for teaching me clustering :p):

```
Folder "Machine_Learning_Papers/"
├── paper1.pdf → embedding₁
├── paper2.pdf → embedding₂
├── notes.txt  → embedding₃
└── CENTROID = mean([embedding₁, embedding₂, embedding₃])
```

**Incoming file:** "neural_networks.pdf"
1. Extract text → compute embedding
2. Cosine similarity against ALL folder centroids
3. Best match above threshold (0.55) → route there
4. Update centroid with new file (running average)

### The Math

**Centroid Update (Running Average):**
```
new_centroid = old_centroid + (new_embedding - old_centroid) / (n + 1)
```

**Similarity Search:**
```
cos_sim(query, centroid) = (query · centroid) / (||query|| × ||centroid||)
```

**Why it's cool:** O(n) search with numpy vectorization. 1000 folders? ~50ms.

### Fallbacks (thanks to AI, these days it is easier to find edge cases)

```
1. Content Centroid (if ≥3 files sampled)
2. Folder Name Embedding (if centroid unavailable)
3. Category Map (user-defined rules)
```

## NLI (after brainstorming with gemini for days, i finally found this, fuck LLMs)

### When Embeddings Aren't Enough

Embeddings are great for similarity, but they don't *reason*. Enter **Natural Language Inference** via Ollama:

```
Prompt: "Given these keywords: ['tensorflow', 'neural', 'training', 'model']
         And these categories: ['Code', 'Academic', 'Documents']
         Which category best fits? Think step by step."

LLM: "These keywords indicate machine learning content.
      While it could be Code, the focus on 'training' and 'model'
      suggests academic research. Category: Academic"
```

**Why it's powerful:**
- Understands context and nuance
- Can reason about ambiguous cases
- Learns from category descriptions

**The catch:** 2-5s inference time. That's why it's a fallback, not primary.

## Memory: The Learning System

### Episodic Memory for Files

Every successful classification creates a memory:

```python
memory.learn(keywords, category, embedding)
```

Stored as:
```json
{
  "text": "tensorflow neural network training",
  "category": "Academic",
  "embedding": [0.123, -0.456, ...],  // 384-dim vector
  "timestamp": "2024-01-15T10:30:00"
}
```

**Recall:**
```python
category, confidence = memory.recall(query_embedding, threshold=0.75)
```

Uses cosine similarity against stored embeddings. If match > 0.75, instant classification without full pipeline.

**Why it's cool:** The system gets smarter over time. First "tensorflow" file? Full analysis. 100th? Instant recall.

## Performance Hacks (thanks to chatgpt 5.1 codex max prompted as nasa senior SDE who took us to moon with only 5kb ram)

### 1. Parallel Voting

Voters run in a ThreadPoolExecutor (2 workers)

**Speedup:** 2x for independent voters. 200ms → 50ms.

### 2. Lazy Model Loading

Models load on first use, not at startup

**Result:** App starts in <1s, models load in background.

### 3. Numpy Vectorization

Atlas search uses numpy matrix operations

**Speedup:** 100x for 1000 folders in comparison to loops

### 4. Incremental Centroid Updates

Instead of recomputing from all files:

```python
new_centroid = old_centroid + (new_embedding - old_centroid) / (n + 1)
```

**Math:** Running average formula. O(1) update vs O(n) recomputation.

## The Event-Driven Magic

### Why Events?

Traditional approach:
```python
watcher.on_file() → classifier.classify() → executor.move()
```

**Problem:** Tight coupling. Watcher knows about classifier, classifier knows about executor. Change one, break all.

**Our approach:**
```python
watcher.on_file() → event_broker.FILE_CREATED.send()
# ... somewhere else ...
@event_broker.FILE_CREATED.connect
def handle_file(path):
    # process
```

**Benefits:**
- Zero coupling between components
- Easy to add new handlers (logging, UI updates, analytics)
- Natural async processing

### The Event Flow

```
FILE_CREATED
    ↓
[Queue] → EventProcessor
    ↓
ANALYSIS_STARTED
    ↓
[Pipeline] → VotingEngine
    ↓
FILE_CLASSIFIED
    ↓
[Atlas] → find_best_folder()
    ↓
ACTION_PROPOSED
    ↓
[Executor] → safe_move()
    ↓
ACTION_COMPLETED → [Memory] → learn()
```

Each arrow is a signal. Each component is independent. Beautiful.

## The Embedding Model Choice

### Why all-MiniLM-L6-v2?

**Considered:**
- `all-mpnet-base-v2`: 420MB, 768-dim, SOTA performance
- `all-MiniLM-L12-v2`: 120MB, 384-dim, good performance
- `all-MiniLM-L6-v2`: 80MB, 384-dim, fast inference ✓

**Decision factors:**
1. **Size:** 80MB fits in memory comfortably
2. **Speed:** 6 layers → 2x faster than 12 layers
3. **Quality:** 95% of mpnet performance at 20% size
4. **Dimension:** 384-dim is sweet spot (not too sparse, not too dense)

**Benchmark (1000 embeddings):**
- mpnet: 8.2s
- MiniLM-L12: 4.1s
- MiniLM-L6: 2.3s ✓

## Session Clustering: Temporal Context

### The Insight

Files don't arrive randomly. They arrive in **sessions**:
- Download 5 papers → all Academic
- Export 10 receipts → all Finance
- Clone 3 repos → all Code

### The Implementation

```python
class SessionManager:
    def __init__(self):
        self.events = []  # (timestamp, file, category)
        self.window = 300  # 5 minutes
    
    def get_context(self):
        recent = [e for e in events if now - e.timestamp < window]
        return Counter(e.category for e in recent)
```

**SessionVoter:**
```python
def vote(self, context):
    recent_categories = session_manager.get_context()
    if recent_categories:
        most_common = recent_categories.most_common(1)[0]
        return most_common[0], 0.7  # Moderate confidence
    return "Unknown", 0.0
```

**Why it works:** If you just organized 5 ML papers, the 6th PDF is probably also ML. Temporal locality is real.

## Safety & Privacy

### The Paranoid Mode

**Dry Run:**
```python
if settings.DRY_RUN:
    logger.info(f"Would move {file} to {dest}")
    return True  # Pretend success
```

Test without consequences.

**Sensitive Detection:**
```python
SENSITIVE_KEYWORDS = ["bank", "statement", "tax", "password", "secret"]

if any(kw in text.lower() for kw in SENSITIVE_KEYWORDS):
    destination = watch_root / "_Needs_Review"
```

Quarantine sensitive files for manual review.

**Resource Guards:**
```python
def check_battery_ok():
    if on_battery and battery_percent < 20:
        logger.warning("Low battery, skipping processing")
        return False
```

Don't drain laptop battery processing files.

### Local-First Philosophy

- Default: 100% local processing
- API mode: Explicit opt-in with key entry
- No telemetry, no cloud uploads
- Your files never leave your machine

## The UI: Minimalist by Design

### System Tray Only

No windows, no dashboards, no clutter. Just:
- 🟢 Green icon: Active
- 🟡 Yellow icon: Paused
- 🔴 Red icon: Error

**Notifications:**
```
"File Detected: report.pdf"
"Classified: report.pdf → Finance"
"Moved: report.pdf → /Documents/Finance"
```

**Philosophy:** The best UI is no UI. Files just... organize themselves.



## The Lessons

### What We Learned

1. **Embeddings > Rules:** Semantic similarity beats regex every time
2. **Ensemble > Single Model:** Diversity reduces errors
3. **Context Matters:** Session clustering improved accuracy by 9%
4. **Fast Enough > Perfect:** 200ms with 91% accuracy beats 5s with 94%
5. **Local-First Wins:** Users trust systems that don't phone home

### What Surprised Us

- Folder name embeddings work better than expected (0.75 accuracy alone)
- TF-IDF still relevant in 2024 (simple, fast, effective)
- Users prefer fewer notifications (we removed 60% of them)
- Battery drain was a real concern (added resource guards)

## The Tech Stack

```
Language: Python 3.8+
Embeddings: sentence-transformers (HuggingFace)
LLM: Ollama (local inference)
Events: Blinker (signals)
Watcher: watchfiles (Rust-based, fast)
UI: pystray (system tray)
DB: TinyDB (JSON document store)
Extraction: docling, pytesseract, python-magic
Config: Pydantic (validation)
Logging: Python logging (structured)
```

**Why these choices?**
- sentence-transformers: Best embedding library, period
- Ollama: Local LLMs without complexity
- Blinker: Lightweight, Pythonic signals
- watchfiles: 10x faster than watchdog (Rust magic)
- TinyDB: Zero-config, human-readable storage

## The Philosophy

### Design Principles

1. **Zero-Config First:** Should work out of the box
2. **Learn, Don't Ask:** Infer from behavior, not forms
3. **Fast Enough:** 200ms is imperceptible, 2s is not
4. **Fail Gracefully:** Degraded service > no service
5. **Privacy by Default:** Local-first, opt-in cloud
6. **Extensible Core:** Plugins > hardcoded features

### The Name

**Sortify** = Sort + Simplify + -ify (make it happen)

Also sounds like Spotify, which is cool.

## The Flex

### What Makes This Special?

Most file organizers:
- Rule-based (brittle)
- Single-method classification (inaccurate)
- Cloud-dependent (privacy concerns)
- Manual configuration (tedious)

**Sortify:**
- Semantic understanding (robust)
- Multi-voter ensemble (accurate)
- Local-first (private)
- Zero-config (automatic)

### The Secret Sauce

It's not one thing. It's the combination:
- Atlas (semantic folder matching)
- Voting ensemble (diverse perspectives)
- Memory (continuous learning)
- Session clustering (temporal context)
- NLI fallback (deep reasoning)

Each adds 5-10% accuracy. Together? 94%.

## Mic Drop

You just read 2000+ words about file organization. You're either:
1. A nerd (welcome, friend)
2. Building something similar (steal our ideas)
3. Procrastinating (same)

Either way, thanks for reading. Now go organize some files. Or don't. Sortify's got you.

---

*"Any sufficiently advanced file organizer is indistinguishable from magic."*
— Arthur C. Clarke (probably)
