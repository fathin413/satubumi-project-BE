-- ============================================================================
-- SATUBUMI - COMPLETE DATABASE SCHEMA FOR SUPABASE
-- Run this script in the Supabase SQL Editor of your new project
-- ============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- 2. CORE TABLES & INDEXES
CREATE TABLE insight_topics (
	id SERIAL NOT NULL, 
	slug VARCHAR(50) NOT NULL, 
	label_id VARCHAR(100) NOT NULL, 
	label_en VARCHAR(100) NOT NULL, 
	created_by VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_insight_topics_id ON insight_topics (id);

CREATE UNIQUE INDEX ix_insight_topics_slug ON insight_topics (slug);

CREATE TABLE rulebooks (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	file_url VARCHAR(500) NOT NULL, 
	thumbnail_url VARCHAR(500), 
	status VARCHAR(30), 
	download_count INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_rulebooks_id ON rulebooks (id);

CREATE TABLE team_members (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	role VARCHAR(150) NOT NULL, 
	description TEXT, 
	image_url VARCHAR(500), 
	"order" INTEGER, 
	is_active BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_team_members_id ON team_members (id);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255), 
	phone_number VARCHAR(50), 
	profile_image VARCHAR(500), 
	role VARCHAR(50), 
	is_active BOOLEAN, 
	has_rapidfs_access BOOLEAN NOT NULL, 
	rapidfs_request_status VARCHAR(50), 
	rapidfs_requested_at TIMESTAMP WITHOUT TIME ZONE, 
	rapidfs_request_project VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_users_id ON users (id);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE activity_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(50) NOT NULL, 
	module VARCHAR(100) NOT NULL, 
	target_id INTEGER, 
	target_name VARCHAR(255), 
	description TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_activity_logs_id ON activity_logs (id);

CREATE TABLE articles (
	id SERIAL NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	title_en VARCHAR(255), 
	slug VARCHAR(255), 
	author VARCHAR(255), 
	author_id INTEGER, 
	content TEXT NOT NULL, 
	content_en TEXT, 
	status VARCHAR(30), 
	tags VARCHAR(255), 
	image_url VARCHAR(500), 
	topic VARCHAR(50), 
	is_featured BOOLEAN, 
	view_count INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(author_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_articles_slug ON articles (slug);

CREATE INDEX ix_articles_category ON articles (category);

CREATE INDEX ix_articles_is_featured ON articles (is_featured);

CREATE INDEX ix_articles_id ON articles (id);

CREATE INDEX ix_articles_topic ON articles (topic);

CREATE TABLE assessments (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	submitter_name VARCHAR(255), 
	submitter_phone VARCHAR(50), 
	submitter_email VARCHAR(255), 
	location_name VARCHAR(255) NOT NULL, 
	area_ha FLOAT NOT NULL, 
	ecosystem_type VARCHAR(100) NOT NULL, 
	project_duration_years INTEGER, 
	carbon_price_usd FLOAT, 
	agb_ton FLOAT, 
	carbon_stock_tc FLOAT, 
	co2e_ton FLOAT, 
	acc_total_credits FLOAT, 
	gross_revenue_usd FLOAT, 
	total_cost_usd FLOAT, 
	net_revenue_usd FLOAT, 
	feasibility_score FLOAT NOT NULL, 
	feasibility_category VARCHAR(100) NOT NULL, 
	component_scores_json JSON, 
	cost_breakdown_json JSON, 
	geometry_geojson JSON, 
	recommendations_json JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_assessments_id ON assessments (id);

CREATE TABLE projects (
	id SERIAL NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	location_name VARCHAR(255) NOT NULL, 
	area_ha FLOAT, 
	status VARCHAR(50) NOT NULL, 
	project_type VARCHAR(100), 
	start_date DATE, 
	end_date DATE, 
	country VARCHAR(100), 
	province VARCHAR(100), 
	district VARCHAR(100), 
	boundary_geojson JSON, 
	targets_json JSON, 
	created_by INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_projects_id ON projects (id);

CREATE TABLE rulebook_downloads (
	id SERIAL NOT NULL, 
	rulebook_id INTEGER, 
	name VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(50) NOT NULL, 
	institution VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(rulebook_id) REFERENCES rulebooks (id)
);

CREATE INDEX ix_rulebook_downloads_id ON rulebook_downloads (id);

CREATE TABLE alerts (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	alert_type VARCHAR(100) NOT NULL, 
	severity VARCHAR(50) NOT NULL, 
	location_geojson JSON, 
	description TEXT NOT NULL, 
	is_read BOOLEAN, 
	is_resolved BOOLEAN, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	auto_generated BOOLEAN, 
	created_by INTEGER, 
	source_url VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_alerts_id ON alerts (id);

CREATE INDEX ix_alerts_project_id ON alerts (project_id);

CREATE TABLE biodiversity_observations (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	species_name VARCHAR(255) NOT NULL, 
	species_type VARCHAR(50) NOT NULL, 
	location_geojson JSON, 
	observed_date DATE NOT NULL, 
	habitat VARCHAR(255), 
	observer VARCHAR(255), 
	photo_url VARCHAR(500), 
	photo_urls JSON, 
	video_urls JSON, 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_biodiversity_observations_project_id ON biodiversity_observations (project_id);

CREATE INDEX ix_biodiversity_observations_id ON biodiversity_observations (id);

CREATE TABLE carbon_records (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	carbon_stock_tco2e FLOAT, 
	biomass_ton FLOAT, 
	estimated_co2e FLOAT, 
	carbon_change FLOAT, 
	methodology VARCHAR(255), 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_carbon_records_id ON carbon_records (id);

CREATE INDEX ix_carbon_records_project_id ON carbon_records (project_id);

CREATE TABLE community_data (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	village_name VARCHAR(255) NOT NULL, 
	beneficiary_count INTEGER, 
	livelihood_groups INTEGER, 
	employment_count INTEGER, 
	community_investment FLOAT, 
	activity_type VARCHAR(100), 
	description TEXT, 
	date DATE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_community_data_project_id ON community_data (project_id);

CREATE INDEX ix_community_data_id ON community_data (id);

CREATE TABLE landscape_snapshots (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	snapshot_date DATE NOT NULL, 
	data_source VARCHAR(100), 
	forest_cover_ha FLOAT, 
	deforestation_ha FLOAT, 
	restoration_ha FLOAT, 
	land_cleared_ha FLOAT, 
	fire_ha FLOAT, 
	ndvi_mean FLOAT, 
	ndvi_min FLOAT, 
	ndvi_max FLOAT, 
	geojson_data JSON, 
	notes TEXT, 
	created_by INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_landscape_snapshots_project_id ON landscape_snapshots (project_id);

CREATE INDEX ix_landscape_snapshots_id ON landscape_snapshots (id);

CREATE TABLE monitoring_plots (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	plot_code VARCHAR(100) NOT NULL, 
	plot_name VARCHAR(255), 
	plot_type VARCHAR(50), 
	location_geojson JSON, 
	area_ha FLOAT, 
	stratum VARCHAR(100), 
	elevation_mdpl FLOAT, 
	slope_pct FLOAT, 
	shape_type VARCHAR(50), 
	dimension_length_m FLOAT, 
	dimension_width_m FLOAT, 
	azimuth_deg FLOAT, 
	established_date DATE, 
	last_survey_date DATE, 
	status VARCHAR(50) NOT NULL, 
	notes TEXT, 
	created_by INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_monitoring_plots_project_id ON monitoring_plots (project_id);

CREATE INDEX ix_monitoring_plots_id ON monitoring_plots (id);

CREATE TABLE project_activities (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	activity_type VARCHAR(100) NOT NULL, 
	activity_date DATE NOT NULL, 
	location_geojson JSON, 
	target FLOAT, 
	realization FLOAT, 
	unit VARCHAR(50), 
	executor VARCHAR(255), 
	photo_urls JSON, 
	notes TEXT, 
	created_by INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_project_activities_project_id ON project_activities (project_id);

CREATE INDEX ix_project_activities_id ON project_activities (id);

CREATE TABLE project_members (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	role VARCHAR(50) NOT NULL, 
	assigned_at TIMESTAMP WITHOUT TIME ZONE, 
	assigned_by INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_project_member UNIQUE (project_id, user_id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
);

CREATE INDEX ix_project_members_user_id ON project_members (user_id);

CREATE INDEX ix_project_members_id ON project_members (id);

CREATE INDEX ix_project_members_project_id ON project_members (project_id);

CREATE TABLE tree_records (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	plot_id VARCHAR(100), 
	tree_tag VARCHAR(100), 
	species VARCHAR(255) NOT NULL, 
	local_name VARCHAR(255), 
	quantity INTEGER NOT NULL, 
	planting_date DATE NOT NULL, 
	location_geojson JSON, 
	condition VARCHAR(50), 
	height_cm FLOAT, 
	dbh_cm FLOAT, 
	circumference_cm FLOAT, 
	is_tag_lost BOOLEAN NOT NULL, 
	is_alive BOOLEAN, 
	photo_urls JSON, 
	notes TEXT, 
	last_monitored TIMESTAMP WITHOUT TIME ZONE, 
	created_by INTEGER, 
	created_by_name VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_tree_records_project_id ON tree_records (project_id);

CREATE INDEX ix_tree_records_id ON tree_records (id);

CREATE INDEX ix_tree_records_tree_tag ON tree_records (tree_tag);

CREATE TABLE field_reports (
	id SERIAL NOT NULL, 
	project_id INTEGER NOT NULL, 
	officer_name VARCHAR(255) NOT NULL, 
	plot_id VARCHAR(100), 
	location_geojson JSON, 
	report_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	report_type VARCHAR(100) NOT NULL, 
	activity_description TEXT, 
	result_description TEXT, 
	photo_urls JSON, 
	video_urls JSON, 
	tree_record_id INTEGER, 
	biodiversity_id INTEGER, 
	created_by INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(tree_record_id) REFERENCES tree_records (id), 
	FOREIGN KEY(biodiversity_id) REFERENCES biodiversity_observations (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_field_reports_project_id ON field_reports (project_id);

CREATE INDEX ix_field_reports_id ON field_reports (id);

CREATE TABLE tree_measurements (
	id SERIAL NOT NULL, 
	tree_record_id INTEGER NOT NULL, 
	project_id INTEGER NOT NULL, 
	measurement_date DATE NOT NULL, 
	height_cm FLOAT, 
	dbh_cm FLOAT, 
	circumference_cm FLOAT, 
	condition VARCHAR(50), 
	is_alive BOOLEAN, 
	measured_by VARCHAR(255), 
	photo_urls JSON, 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tree_record_id) REFERENCES tree_records (id) ON DELETE CASCADE, 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_tree_measurements_project_id ON tree_measurements (project_id);

CREATE INDEX ix_tree_measurements_id ON tree_measurements (id);

CREATE INDEX ix_tree_measurements_tree_record_id ON tree_measurements (tree_record_id);

-- 3. SUPABASE STORAGE SETUP
-- Create bucket 'satubumi-public' if it doesn't already exist

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'satubumi-public',
    'satubumi-public',
    true,
    10485760, -- 10MB limit
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'application/pdf', 'application/geo+json', 'application/json']
)
ON CONFLICT (id) DO UPDATE SET public = true;

-- Storage Policies for 'satubumi-public'

-- Allow public read access to all files in satubumi-public
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING (bucket_id = 'satubumi-public');

-- Allow service_role and authenticated users to upload/update/delete
DROP POLICY IF EXISTS "Service Role & Authenticated Upload" ON storage.objects;
CREATE POLICY "Service Role & Authenticated Upload"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'satubumi-public');

DROP POLICY IF EXISTS "Service Role & Authenticated Update" ON storage.objects;
CREATE POLICY "Service Role & Authenticated Update"
ON storage.objects FOR UPDATE
USING (bucket_id = 'satubumi-public');

DROP POLICY IF EXISTS "Service Role & Authenticated Delete" ON storage.objects;
CREATE POLICY "Service Role & Authenticated Delete"
ON storage.objects FOR DELETE
USING (bucket_id = 'satubumi-public');

-- 4. ROW LEVEL SECURITY (RLS) & APPLICATION ACCESS

-- Since the backend uses direct PostgreSQL connection with service credentials / postgres role,
-- we grant full permissions on public schema to service_role and postgres,
-- and enable RLS policies allowing authenticated / service operations.

ALTER TABLE insight_topics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "insight_topics_service_all" ON insight_topics;
CREATE POLICY "insight_topics_service_all" ON insight_topics
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE rulebooks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rulebooks_service_all" ON rulebooks;
CREATE POLICY "rulebooks_service_all" ON rulebooks
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "team_members_service_all" ON team_members;
CREATE POLICY "team_members_service_all" ON team_members
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_service_all" ON users;
CREATE POLICY "users_service_all" ON users
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "activity_logs_service_all" ON activity_logs;
CREATE POLICY "activity_logs_service_all" ON activity_logs
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "articles_service_all" ON articles;
CREATE POLICY "articles_service_all" ON articles
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "assessments_service_all" ON assessments;
CREATE POLICY "assessments_service_all" ON assessments
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "projects_service_all" ON projects;
CREATE POLICY "projects_service_all" ON projects
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE rulebook_downloads ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rulebook_downloads_service_all" ON rulebook_downloads;
CREATE POLICY "rulebook_downloads_service_all" ON rulebook_downloads
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "alerts_service_all" ON alerts;
CREATE POLICY "alerts_service_all" ON alerts
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE biodiversity_observations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "biodiversity_observations_service_all" ON biodiversity_observations;
CREATE POLICY "biodiversity_observations_service_all" ON biodiversity_observations
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE carbon_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "carbon_records_service_all" ON carbon_records;
CREATE POLICY "carbon_records_service_all" ON carbon_records
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE community_data ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "community_data_service_all" ON community_data;
CREATE POLICY "community_data_service_all" ON community_data
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE landscape_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "landscape_snapshots_service_all" ON landscape_snapshots;
CREATE POLICY "landscape_snapshots_service_all" ON landscape_snapshots
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE monitoring_plots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "monitoring_plots_service_all" ON monitoring_plots;
CREATE POLICY "monitoring_plots_service_all" ON monitoring_plots
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE project_activities ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "project_activities_service_all" ON project_activities;
CREATE POLICY "project_activities_service_all" ON project_activities
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "project_members_service_all" ON project_members;
CREATE POLICY "project_members_service_all" ON project_members
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE tree_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tree_records_service_all" ON tree_records;
CREATE POLICY "tree_records_service_all" ON tree_records
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE field_reports ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "field_reports_service_all" ON field_reports;
CREATE POLICY "field_reports_service_all" ON field_reports
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);

ALTER TABLE tree_measurements ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tree_measurements_service_all" ON tree_measurements;
CREATE POLICY "tree_measurements_service_all" ON tree_measurements
    FOR ALL
    TO postgres, service_role
    USING (true)
    WITH CHECK (true);
