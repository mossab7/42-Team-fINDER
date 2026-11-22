-- Forward-only SQLite migration for installations that manage schema outside
-- FastAPI startup.  Fresh installs also create these tables through SQLAlchemy
-- metadata in app.core.database.init_db; this file documents the production
-- schema change without modifying or dropping existing scanner data.
CREATE TABLE IF NOT EXISTS student_profiles (
  user_id INTEGER PRIMARY KEY, login VARCHAR(128) NOT NULL, display_name VARCHAR(255) NOT NULL,
  image_url TEXT, campus_id INTEGER, campus_name VARCHAR(255), level FLOAT,
  biography TEXT NOT NULL DEFAULT '', skills JSON NOT NULL DEFAULT '[]', languages JSON NOT NULL DEFAULT '[]',
  availability VARCHAR(120) NOT NULL DEFAULT '', working_hours VARCHAR(120) NOT NULL DEFAULT '',
  github_url VARCHAR(512), visible BOOLEAN NOT NULL DEFAULT 1, updated_at DATETIME NOT NULL
);
CREATE TABLE IF NOT EXISTS swipes (
  id INTEGER PRIMARY KEY, swiper_user_id INTEGER NOT NULL REFERENCES student_profiles(user_id),
  target_user_id INTEGER NOT NULL REFERENCES student_profiles(user_id), project_id INTEGER NOT NULL,
  direction VARCHAR(8) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  CONSTRAINT uq_swipe_pair_project UNIQUE(swiper_user_id,target_user_id,project_id)
);
CREATE TABLE IF NOT EXISTS matches (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, project_name VARCHAR(255) NOT NULL,
  user_low_id INTEGER NOT NULL REFERENCES student_profiles(user_id), user_high_id INTEGER NOT NULL REFERENCES student_profiles(user_id),
  status VARCHAR(20) NOT NULL DEFAULT 'active', created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  CONSTRAINT uq_match_pair_project UNIQUE(project_id,user_low_id,user_high_id)
);
CREATE TABLE IF NOT EXISTS platform_teams (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, project_name VARCHAR(255) NOT NULL, campus_id INTEGER,
  creator_id INTEGER NOT NULL REFERENCES student_profiles(user_id), name VARCHAR(120) NOT NULL,
  description TEXT NOT NULL DEFAULT '', maximum_members INTEGER NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
);
CREATE TABLE IF NOT EXISTS platform_team_members (
  id INTEGER PRIMARY KEY, team_id INTEGER NOT NULL REFERENCES platform_teams(id), user_id INTEGER NOT NULL REFERENCES student_profiles(user_id),
  role VARCHAR(20) NOT NULL DEFAULT 'member', status VARCHAR(20) NOT NULL DEFAULT 'accepted', created_at DATETIME NOT NULL,
  CONSTRAINT uq_platform_team_member UNIQUE(team_id,user_id)
);
CREATE TABLE IF NOT EXISTS team_invitations (
  id INTEGER PRIMARY KEY, team_id INTEGER NOT NULL REFERENCES platform_teams(id), recipient_id INTEGER NOT NULL REFERENCES student_profiles(user_id),
  invited_by_id INTEGER NOT NULL REFERENCES student_profiles(user_id), status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  CONSTRAINT uq_team_invitation_recipient UNIQUE(team_id,recipient_id)
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY, recipient_id INTEGER NOT NULL REFERENCES student_profiles(user_id), type VARCHAR(48) NOT NULL,
  title VARCHAR(255) NOT NULL, body TEXT NOT NULL DEFAULT '', payload JSON NOT NULL DEFAULT '{}',
  read BOOLEAN NOT NULL DEFAULT 0, created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_swipes_target_project ON swipes(target_user_id,project_id);
