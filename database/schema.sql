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

-- Table: notes
CREATE TABLE IF NOT EXISTS notes (
	note_id INTEGER PRIMARY KEY AUTOINCREMENT,
	piece_id INTEGER NOT NULL,
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
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE
);

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
	note_id INTEGER,                 -- 关联到notes表的note_id (起始音符)
	next_note_id INTEGER,            -- 关联到notes表的note_id (结束音符)
	voice INTEGER NOT NULL,
	voice_name TEXT,                 -- 声部名称 (Cantus, Altus, Tenor, Bassus, etc.)
	onset REAL NOT NULL,             -- 音程开始时间
	measure INTEGER,
	beat REAL,
	interval_semitones REAL,         -- 音程的半音数 (从chromatic或quality解析得出)
	interval_type TEXT,              -- 主要音程类型描述 (如 "major 3rd")
	interval_direction TEXT,         -- 音程方向: "ascending", "descending", "unison"
	interval_quality TEXT,           -- 音程性质
	
	-- CRIM音程记号的所有类型
	interval_quality_notation TEXT,     -- 带性质的全音阶音程 (P8, M3, m3)
	interval_diatonic_notation TEXT,    -- 不带性质的全音阶音程 (8, 3)
	interval_chromatic_notation TEXT,   -- 半音程记号 (12, 6, 0)
	interval_zerobased_notation TEXT,   -- 零基全音阶音程 (7, -4, 2)
	
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE,
	FOREIGN KEY (note_id) REFERENCES notes (note_id) ON DELETE SET NULL,
	FOREIGN KEY (next_note_id) REFERENCES notes (note_id) ON DELETE SET NULL
);

-- Indexes for melodic_intervals table
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_piece ON melodic_intervals(piece_id);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_voice ON melodic_intervals(voice);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_onset ON melodic_intervals(onset);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_note ON melodic_intervals(note_id);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_next_note ON melodic_intervals(next_note_id);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_semitones ON melodic_intervals(interval_semitones);
CREATE INDEX IF NOT EXISTS idx_melodic_intervals_direction ON melodic_intervals(interval_direction);
