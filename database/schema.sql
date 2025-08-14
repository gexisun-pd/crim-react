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
	voice INTEGER,                    -- 声部编号 (CRIM: voice)
	onset REAL,                      -- 音符开始时间，以四分音符为单位 (CRIM: offset)
	duration REAL,                   -- 音符时长，以四分音符为单位 (CRIM: duration)
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
