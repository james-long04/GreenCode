-- GreenCode evidence store (PostgreSQL).
-- Generated from backend/app/db/models.py; `python scripts/init_db.py` creates the same tables
-- via SQLAlchemy, this file is kept for reference and for creating the schema by hand.

CREATE TABLE carbon_factors (
	id VARCHAR(36) NOT NULL, 
	region VARCHAR(16) NOT NULL, 
	year INTEGER NOT NULL, 
	grams_co2e_per_kwh FLOAT NOT NULL, 
	source VARCHAR(300) NOT NULL, 
	notes TEXT, 
	is_default BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_carbon_factor UNIQUE (region, year, source)
);

CREATE INDEX ix_carbon_factors_region ON carbon_factors (region);

CREATE TABLE projects (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE analyses (
	id VARCHAR(36) NOT NULL, 
	project_id VARCHAR(36) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	language VARCHAR(16) NOT NULL, 
	source TEXT NOT NULL, 
	case_spec JSON NOT NULL, 
	case_id VARCHAR(100), 
	status VARCHAR(32) NOT NULL, 
	analyser_version VARCHAR(32) NOT NULL, 
	duration_ms FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_analyses_case_id ON analyses (case_id);
CREATE INDEX ix_analyses_project_id ON analyses (project_id);

CREATE TABLE findings (
	id VARCHAR(36) NOT NULL, 
	analysis_id VARCHAR(36) NOT NULL, 
	rule_id VARCHAR(16) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	category VARCHAR(64) NOT NULL, 
	line INTEGER, 
	"column" INTEGER, 
	end_line INTEGER, 
	snippet TEXT, 
	explanation TEXT NOT NULL, 
	suggestion TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	evidence JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE
);

CREATE INDEX ix_findings_rule_id ON findings (rule_id);
CREATE INDEX ix_findings_analysis_id ON findings (analysis_id);

CREATE TABLE optimisations (
	id VARCHAR(36) NOT NULL, 
	analysis_id VARCHAR(36) NOT NULL, 
	condition VARCHAR(32) NOT NULL, 
	original_source TEXT NOT NULL, 
	candidate_source TEXT, 
	model_name VARCHAR(120) NOT NULL, 
	provider VARCHAR(32) NOT NULL, 
	prompt TEXT, 
	raw_response TEXT, 
	generation_ms FLOAT, 
	prompt_tokens INTEGER, 
	completion_tokens INTEGER, 
	status VARCHAR(32) NOT NULL, 
	failure_reason TEXT, 
	summary JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE
);

CREATE INDEX ix_optimisations_condition ON optimisations (condition);
CREATE INDEX ix_optimisations_analysis_id ON optimisations (analysis_id);
CREATE INDEX ix_optimisations_status ON optimisations (status);

CREATE TABLE benchmark_runs (
	id VARCHAR(36) NOT NULL, 
	optimisation_id VARCHAR(36) NOT NULL, 
	variant VARCHAR(16) NOT NULL, 
	repetitions INTEGER NOT NULL, 
	warmup_runs INTEGER NOT NULL, 
	mean_ms FLOAT, 
	median_ms FLOAT, 
	stdev_ms FLOAT, 
	min_ms FLOAT, 
	max_ms FLOAT, 
	ci95_low_ms FLOAT, 
	ci95_high_ms FLOAT, 
	samples_ms JSON NOT NULL, 
	environment JSON NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(optimisation_id) REFERENCES optimisations (id) ON DELETE CASCADE
);

CREATE INDEX ix_benchmark_runs_optimisation_id ON benchmark_runs (optimisation_id);

CREATE TABLE test_results (
	id VARCHAR(36) NOT NULL, 
	optimisation_id VARCHAR(36) NOT NULL, 
	test_name VARCHAR(200) NOT NULL, 
	passed BOOLEAN NOT NULL, 
	failure_type VARCHAR(64), 
	details TEXT, 
	duration_ms FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(optimisation_id) REFERENCES optimisations (id) ON DELETE CASCADE
);

CREATE INDEX ix_test_results_optimisation_id ON test_results (optimisation_id);

CREATE TABLE measurements (
	id VARCHAR(36) NOT NULL, 
	benchmark_run_id VARCHAR(36) NOT NULL, 
	metric VARCHAR(64) NOT NULL, 
	value FLOAT NOT NULL, 
	unit VARCHAR(32) NOT NULL, 
	method VARCHAR(32) NOT NULL, 
	source VARCHAR(64) NOT NULL, 
	carbon_factor_id VARCHAR(36), 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(benchmark_run_id) REFERENCES benchmark_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(carbon_factor_id) REFERENCES carbon_factors (id)
);

CREATE INDEX ix_measurements_benchmark_run_id ON measurements (benchmark_run_id);
