-- MechMind AI Database Schema

-- Equipment table
CREATE TABLE IF NOT EXISTS equipment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    model VARCHAR(255),
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    node_id VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sensor readings table
CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id),
    node_id VARCHAR(100),
    temperature FLOAT,
    vibration_x FLOAT,
    vibration_y FLOAT,
    vibration_z FLOAT,
    vibration_magnitude FLOAT,
    sound_level_db FLOAT,
    vibration_fft JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'warning',
    message TEXT NOT NULL,
    sensor_value FLOAT,
    threshold FLOAT,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Diagnostic sessions (WhatsApp conversations)
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20),
    equipment_id INTEGER REFERENCES equipment(id),
    query_type VARCHAR(50),
    user_message TEXT,
    ai_response TEXT,
    image_url TEXT,
    voice_transcript TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert thresholds config
CREATE TABLE IF NOT EXISTS alert_thresholds (
    id SERIAL PRIMARY KEY,
    equipment_type VARCHAR(100),
    metric VARCHAR(50) NOT NULL,
    warning_threshold FLOAT NOT NULL,
    critical_threshold FLOAT NOT NULL,
    unit VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default thresholds
INSERT INTO alert_thresholds (equipment_type, metric, warning_threshold, critical_threshold, unit) VALUES
    ('excavator', 'temperature', 85.0, 105.0, '°C'),
    ('excavator', 'vibration_magnitude', 4.5, 8.0, 'g'),
    ('excavator', 'sound_level_db', 95.0, 110.0, 'dB'),
    ('loader', 'temperature', 80.0, 100.0, '°C'),
    ('loader', 'vibration_magnitude', 5.0, 9.0, 'g'),
    ('loader', 'sound_level_db', 90.0, 105.0, 'dB'),
    ('crane', 'temperature', 75.0, 95.0, '°C'),
    ('crane', 'vibration_magnitude', 3.0, 6.0, 'g'),
    ('crane', 'sound_level_db', 85.0, 100.0, 'dB'),
    ('generator', 'temperature', 90.0, 110.0, '°C'),
    ('generator', 'vibration_magnitude', 3.5, 7.0, 'g'),
    ('generator', 'sound_level_db', 100.0, 115.0, 'dB');

-- Insert demo equipment
INSERT INTO equipment (name, type, model, location, node_id) VALUES
    ('Excavator CAT 320', 'excavator', 'CAT 320GC', 'Lagos Site A', 'NODE-001'),
    ('Wheel Loader XCMG LW500', 'loader', 'XCMG LW500FN', 'Lagos Site A', 'NODE-002'),
    ('Tower Crane Zoomlion', 'crane', 'Zoomlion TC6013A', 'Abuja Site B', 'NODE-003');

-- Create indexes for performance
CREATE INDEX idx_sensor_readings_equipment ON sensor_readings(equipment_id);
CREATE INDEX idx_sensor_readings_timestamp ON sensor_readings(timestamp DESC);
CREATE INDEX idx_sensor_readings_node ON sensor_readings(node_id);
CREATE INDEX idx_alerts_equipment ON alerts(equipment_id);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);
