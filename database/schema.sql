-- Table: pieces
CREATE TABLE IF NOT EXISTS pieces (
	piece_id INTEGER PRIMARY KEY AUTOINCREMENT,
	path TEXT NOT NULL,
	filename TEXT NOT NULL,
	title TEXT,
	composer TEXT,
	sha256 TEXT,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: note_sets
CREATE TABLE IF NOT EXISTS note_sets (
	set_id INTEGER PRIMARY KEY AUTOINCREMENT,
	combine_unisons BOOLEAN NOT NULL,
	slug TEXT NOT NULL UNIQUE,       -- Short identifier: cT or cF
	description TEXT NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	UNIQUE(combine_unisons)
);

-- Table: melodic_interval_sets
CREATE TABLE IF NOT EXISTS melodic_interval_sets (
	set_id INTEGER PRIMARY KEY AUTOINCREMENT,
	kind TEXT NOT NULL,              -- "quality" or "diatonic"
	note_set_id INTEGER NOT NULL,    -- Reference to note_sets
	slug TEXT NOT NULL UNIQUE,       -- Short identifier: cT_kq, cT_kd, cF_kq, cF_kd
	description TEXT NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (note_set_id) REFERENCES note_sets (set_id) ON DELETE CASCADE,
	UNIQUE(kind, note_set_id)
);

-- Table: melodic_ngram_sets
CREATE TABLE IF NOT EXISTS melodic_ngram_sets (
	set_id INTEGER PRIMARY KEY AUTOINCREMENT,
	melodic_interval_set_id INTEGER NOT NULL, -- Reference to melodic_interval_sets
	ngrams_number INTEGER NOT NULL,  -- Number of n-grams (3-10)
	ngrams_entry BOOLEAN NOT NULL,   -- Whether to include entry points
	parent_set_id INTEGER,           -- Reference to parent set (only for entry=1, points to entry=0 set)
	slug TEXT NOT NULL UNIQUE,       -- Short identifier: cT_kq_n3, cF_kd_n5, etc.
	description TEXT NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (melodic_interval_set_id) REFERENCES melodic_interval_sets (set_id) ON DELETE CASCADE,
	FOREIGN KEY (parent_set_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE,
	UNIQUE(melodic_interval_set_id, ngrams_number, ngrams_entry)
);

-- Table: notes
CREATE TABLE IF NOT EXISTS notes (
	note_id INTEGER PRIMARY KEY AUTOINCREMENT,
	piece_id INTEGER NOT NULL,
	note_set_id INTEGER NOT NULL,        -- Reference to note_sets table
	voice INTEGER,                    -- 声部编号 (1, 2, 3, ...) 
	voice_name TEXT,                 -- 声部名称 (Cantus, Altus, Tenor, Bassus, etc.)
	onset REAL,                      -- 音符开始时间，以四分音符为单位 (CRIM: offset)
	duration REAL,                   -- 音符时长，以四分音符为单位 (CRIM: duration)
	offset REAL,                     -- 音符结束时间 onset+duration
	measure INTEGER,                 -- 小节号 (CRIM: measure)
	beat REAL,                       -- 拍位 (CRIM: beat)
	pitch INTEGER,                   -- MIDI音高数字 (CRIM: pitch)
	name TEXT,                       -- 音名，如C4, D#5 (CRIM: name)
	step TEXT,                       -- 音级，如C, D, E (CRIM: step)
	octave INTEGER,                  -- 八度 (CRIM: octave)
	`alter` INTEGER,                 -- 升降号，-1=降号, 0=自然, 1=升号 (CRIM: alter)
	type TEXT,                       -- 音符类型: Note, Rest (CRIM: type)
	staff INTEGER,                   -- 谱表编号 (CRIM: staff)
	tie TEXT,                        -- 连音线信息 (CRIM: tie)
	is_entry BOOLEAN DEFAULT 0,      -- 是否为入点音符 (entry point)
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
	FOREIGN KEY (note_set_id) REFERENCES note_sets (set_id) ON DELETE CASCADE
);

-- Indexes for notes table
CREATE INDEX IF NOT EXISTS idx_notes_piece ON notes(piece_id);
CREATE INDEX IF NOT EXISTS idx_notes_set ON notes(note_set_id);
CREATE INDEX IF NOT EXISTS idx_notes_voice ON notes(voice);
CREATE INDEX IF NOT EXISTS idx_notes_onset ON notes(onset);
CREATE INDEX IF NOT EXISTS idx_notes_pitch ON notes(pitch);
CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(type);
CREATE INDEX IF NOT EXISTS idx_notes_is_entry ON notes(is_entry);

-- Table: parameter_sets
CREATE TABLE IF NOT EXISTS parameter_sets (
	parameter_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
	description TEXT NOT NULL,       -- 参数组合的描述，如 "4_q_cT"
	kind TEXT NOT NULL,              -- 音程类型: "quality" 或 "diatonic"
	combine_unisons BOOLEAN NOT NULL, -- 是否合并齐音: true 或 false
	number INTEGER NOT NULL,         -- 音程数字: 3-10
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	UNIQUE(kind, combine_unisons, number)  -- 确保参数组合唯一
);

-- Table: melodic_intervals
CREATE TABLE IF NOT EXISTS melodic_intervals (
	interval_id INTEGER PRIMARY KEY AUTOINCREMENT,
	piece_id INTEGER NOT NULL,
	melodic_interval_set_id INTEGER NOT NULL, -- 关联到melodic_interval_sets表
	note_id INTEGER,                 -- Reference to the starting note of this interval
	voice INTEGER NOT NULL,
	voice_name TEXT,                 -- 声部名称 (Cantus, Altus, Tenor, Bassus, etc.)
	onset REAL NOT NULL,             -- 音程开始时间
	interval_type TEXT,              -- CRIM原始输出值 (P1, m2, M3 或 1, 2, 3)
	
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
	FOREIGN KEY (melodic_interval_set_id) REFERENCES melodic_interval_sets (set_id) ON DELETE CASCADE,
	FOREIGN KEY (note_id) REFERENCES notes (note_id) ON DELETE CASCADE
);

-- Indexes for melodic_intervals table
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_piece ON melodic_intervals(piece_id);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_set ON melodic_intervals(melodic_interval_set_id);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_note ON melodic_intervals(note_id);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_voice ON melodic_intervals(voice);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_onset ON melodic_intervals(onset);

-- Table: melodic_ngrams
CREATE TABLE IF NOT EXISTS melodic_ngrams (
	ngram_id INTEGER PRIMARY KEY AUTOINCREMENT,
	piece_id INTEGER NOT NULL,
	melodic_ngram_set_id INTEGER NOT NULL,  -- Reference to melodic_ngram_sets
	note_id INTEGER,                        -- Reference to the starting note of this n-gram
	voice INTEGER NOT NULL,
	voice_name TEXT,                        -- Voice name (Cantus, Altus, Tenor, Bassus, etc.)
	onset REAL NOT NULL,                    -- N-gram onset time (start time of first interval)
	ngram TEXT NOT NULL,                    -- The n-gram pattern (comma-separated intervals)
	ngram_length INTEGER NOT NULL,          -- Length of the n-gram (3, 4, 5, etc.)
	
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
	FOREIGN KEY (melodic_ngram_set_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE,
	FOREIGN KEY (note_id) REFERENCES notes (note_id) ON DELETE CASCADE
);

-- Indexes for melodic_ngrams table
CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_piece ON melodic_ngrams(piece_id);
CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_set ON melodic_ngrams(melodic_ngram_set_id);
CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_note ON melodic_ngrams(note_id);
CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_voice ON melodic_ngrams(voice);
CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_onset ON melodic_ngrams(onset);
CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_pattern ON melodic_ngrams(ngram);
CREATE INDEX IF NOT EXISTS idx_melodic_ngrams_length ON melodic_ngrams(ngram_length);

-- Table: melodic_entries
CREATE TABLE IF NOT EXISTS melodic_entries (
	entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
	piece_id INTEGER NOT NULL,
	melodic_ngram_set_id INTEGER NOT NULL,  -- Reference to melodic_ngram_sets where ngrams_entry = True
	note_id INTEGER,                        -- Reference to the starting note of this entry
	voice INTEGER NOT NULL,
	voice_name TEXT,                        -- Voice name (Cantus, Altus, Tenor, Bassus, etc.)
	onset REAL NOT NULL,                    -- Entry onset time (start time of first interval)
	entry_pattern TEXT NOT NULL,            -- The entry pattern (comma-separated intervals)
	entry_length INTEGER NOT NULL,          -- Length of the entry (3, 4, 5, etc.)
	is_thematic BOOLEAN NOT NULL DEFAULT 0, -- Whether this entry is thematic (appears multiple times)
	from_rest BOOLEAN NOT NULL DEFAULT 1,   -- Whether this entry starts after rest/break/fermata
	
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
	FOREIGN KEY (melodic_ngram_set_id) REFERENCES melodic_ngram_sets (set_id) ON DELETE CASCADE,
	FOREIGN KEY (note_id) REFERENCES notes (note_id) ON DELETE CASCADE
);

-- Indexes for melodic_entries table
CREATE INDEX IF NOT EXISTS idx_melodic_entries_piece ON melodic_entries(piece_id);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_set ON melodic_entries(melodic_ngram_set_id);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_note ON melodic_entries(note_id);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_voice ON melodic_entries(voice);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_onset ON melodic_entries(onset);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_pattern ON melodic_entries(entry_pattern);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_length ON melodic_entries(entry_length);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_thematic ON melodic_entries(is_thematic);
CREATE INDEX IF NOT EXISTS idx_melodic_entries_from_rest ON melodic_entries(from_rest);
