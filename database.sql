-- =========================================================================
-- tapsyrma — PostgreSQL (Railway)
-- =========================================================================

-- BATCH
DROP TABLE IF EXISTS "AuditLog" CASCADE;
DROP TABLE IF EXISTS "Reviews" CASCADE;
DROP TABLE IF EXISTS "TeacherBadges" CASCADE;
DROP TABLE IF EXISTS "Badges" CASCADE;
DROP TABLE IF EXISTS "Events" CASCADE;
DROP TABLE IF EXISTS "Achievements" CASCADE;
DROP TABLE IF EXISTS "AchievementTypes" CASCADE;
DROP TABLE IF EXISTS "Teachers" CASCADE;
DROP TABLE IF EXISTS "Admins" CASCADE;

-- BATCH
CREATE TABLE "Admins" (
    "AdminId"       SERIAL PRIMARY KEY,
    "Username"      VARCHAR(100) NOT NULL UNIQUE,
    "FullName"      VARCHAR(200),
    "Email"         VARCHAR(100) UNIQUE,
    "PasswordHash"  VARCHAR(255) NOT NULL,
    "Role"          VARCHAR(30) NOT NULL DEFAULT 'superadmin',
    "CreatedAt"     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- BATCH
CREATE TABLE "Teachers" (
    "TeacherId"     SERIAL PRIMARY KEY,
    "FullName"      VARCHAR(200) NOT NULL,
    "Login"         VARCHAR(100) NOT NULL UNIQUE,
    "PasswordHash"  VARCHAR(255) NOT NULL,
    "Department"    VARCHAR(200),
    "Position"      VARCHAR(200),
    "Email"         VARCHAR(200),
    "PhotoPath"     VARCHAR(500),
    "TotalScore"    INT NOT NULL DEFAULT 0,
    "IsBlocked"     BOOLEAN NOT NULL DEFAULT FALSE,
    "YearlyGoal"    INT,
    "LastLoginAt"   TIMESTAMP,
    "Bio"           VARCHAR(2000),
    "Phone"         VARCHAR(50),
    "CreatedAt"     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- BATCH
CREATE TABLE "AchievementTypes" (
    "TypeId"    SERIAL PRIMARY KEY,
    "TypeName"  VARCHAR(200) NOT NULL,
    "Category"  VARCHAR(100) NOT NULL DEFAULT 'Жалпы',
    "Score"     INT NOT NULL
);

-- BATCH
CREATE TABLE "Achievements" (
    "AchievementId"  SERIAL PRIMARY KEY,
    "TeacherId"      INT NOT NULL REFERENCES "Teachers"("TeacherId"),
    "TypeId"         INT NOT NULL REFERENCES "AchievementTypes"("TypeId"),
    "Title"          VARCHAR(300) NOT NULL,
    "Description"    VARCHAR(2000),
    "ImagePath"      VARCHAR(500),
    "IsApproved"     BOOLEAN NOT NULL DEFAULT FALSE,
    "IsRejected"     BOOLEAN NOT NULL DEFAULT FALSE,
    "RejectReason"   VARCHAR(500),
    "Score"          INT NOT NULL DEFAULT 0,
    "SubmittedAt"    TIMESTAMP NOT NULL DEFAULT NOW(),
    "ApprovedAt"     TIMESTAMP,
    "AcademicYear"   VARCHAR(20)
);

-- BATCH
CREATE TABLE "SiteSettings" (
    "SettingKey"   VARCHAR(100) PRIMARY KEY,
    "SettingValue" TEXT,
    "UpdatedAt"    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- BATCH
CREATE TABLE "DepartmentGoals" (
    "GoalId"       SERIAL PRIMARY KEY,
    "Department"   VARCHAR(200) NOT NULL,
    "AcademicYear" VARCHAR(20) NOT NULL,
    "YearlyGoal"   INT NOT NULL DEFAULT 0,
    UNIQUE ("Department", "AcademicYear")
);

-- BATCH
CREATE TABLE "Badges" (
    "BadgeId"      SERIAL PRIMARY KEY,
    "BadgeName"    VARCHAR(100) NOT NULL UNIQUE,
    "Icon"         VARCHAR(50) NOT NULL,
    "Color"        VARCHAR(20) NOT NULL DEFAULT '#ffd700',
    "Description"  VARCHAR(300),
    "MinScore"     INT NOT NULL DEFAULT 0
);

-- BATCH
CREATE TABLE "TeacherBadges" (
    "TeacherBadgeId"  SERIAL PRIMARY KEY,
    "TeacherId"       INT NOT NULL REFERENCES "Teachers"("TeacherId"),
    "BadgeId"         INT NOT NULL REFERENCES "Badges"("BadgeId"),
    "AwardedAt"       TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE ("TeacherId", "BadgeId")
);

-- BATCH
CREATE TABLE "Reviews" (
    "ReviewId"    SERIAL PRIMARY KEY,
    "TeacherId"   INT NOT NULL REFERENCES "Teachers"("TeacherId"),
    "ReviewerId"  INT REFERENCES "Teachers"("TeacherId"),
    "Stars"       INT NOT NULL CHECK ("Stars" BETWEEN 1 AND 5),
    "Comment"     VARCHAR(1000),
    "CreatedAt"   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- BATCH
CREATE TABLE "Events" (
    "EventId"      SERIAL PRIMARY KEY,
    "Title"        VARCHAR(300) NOT NULL,
    "Description"  VARCHAR(2000),
    "EventDate"    TIMESTAMP NOT NULL,
    "CreatedAt"    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- BATCH
CREATE TABLE "AuditLog" (
    "LogId"      SERIAL PRIMARY KEY,
    "UserType"   VARCHAR(20) NOT NULL,
    "UserId"     INT,
    "Action"     VARCHAR(100) NOT NULL,
    "Details"    VARCHAR(500),
    "IpAddress"  VARCHAR(50),
    "CreatedAt"  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- BATCH
CREATE OR REPLACE FUNCTION trg_update_teacher_score() RETURNS TRIGGER AS $$
DECLARE
    tid INT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        tid := OLD."TeacherId";
    ELSE
        tid := NEW."TeacherId";
    END IF;
    UPDATE "Teachers" t SET "TotalScore" = COALESCE((
        SELECT SUM(a."Score") FROM "Achievements" a
        WHERE a."TeacherId" = tid AND a."IsApproved" = TRUE
    ), 0) WHERE t."TeacherId" = tid;
    IF TG_OP = 'UPDATE' AND OLD."TeacherId" IS DISTINCT FROM NEW."TeacherId" THEN
        UPDATE "Teachers" t SET "TotalScore" = COALESCE((
            SELECT SUM(a."Score") FROM "Achievements" a
            WHERE a."TeacherId" = OLD."TeacherId" AND a."IsApproved" = TRUE
        ), 0) WHERE t."TeacherId" = OLD."TeacherId";
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_achievements_score ON "Achievements";
CREATE TRIGGER trg_achievements_score
    AFTER INSERT OR UPDATE OR DELETE ON "Achievements"
    FOR EACH ROW EXECUTE FUNCTION trg_update_teacher_score();

-- BATCH
DROP VIEW IF EXISTS "vw_TeacherRating";

CREATE VIEW "vw_TeacherRating" AS
SELECT
    t."TeacherId",
    t."FullName",
    t."Login",
    t."Department",
    t."Position",
    t."Email",
    t."PhotoPath",
    t."TotalScore",
    t."IsBlocked",
    t."YearlyGoal",
    t."LastLoginAt",
    t."Bio",
    t."Phone",
    (SELECT COUNT(*) FROM "Achievements" a
     WHERE a."TeacherId" = t."TeacherId" AND a."IsApproved" = TRUE) AS ApprovedCount,
    (SELECT COUNT(*) FROM "Achievements" a
     WHERE a."TeacherId" = t."TeacherId" AND a."IsApproved" = FALSE AND a."IsRejected" = FALSE) AS PendingCount,
    (SELECT COUNT(*) FROM "Achievements" a
     WHERE a."TeacherId" = t."TeacherId" AND a."IsRejected" = TRUE) AS RejectedCount,
    COALESCE((SELECT AVG("Stars"::numeric) FROM "Reviews" r
            WHERE r."TeacherId" = t."TeacherId"), 0) AS AvgRating,
    (SELECT COUNT(*) FROM "Reviews" r WHERE r."TeacherId" = t."TeacherId") AS ReviewsCount,
    DENSE_RANK() OVER (ORDER BY t."TotalScore" DESC) AS RankPosition
FROM "Teachers" t;

-- BATCH
INSERT INTO "AchievementTypes" ("TypeName", "Category", "Score") VALUES
('Халықаралық олимпиада / конференция жеңісі',     'Халықаралық',   15),
('Республикалық олимпиада / конференция жеңісі',   'Республикалық', 10),
('Облыстық жарыс / олимпиада жеңісі',              'Облыстық',       7),
('Қалалық / аудандық жеңіс',                        'Қалалық',        5),
('Ғылыми мақала (жоғары рейтингтік журнал)',       'Ғылыми еңбек',   8),
('Ғылыми мақала (кәдімгі журнал)',                 'Ғылыми еңбек',   5),
('Оқу-әдістемелік құрал',                          'Әдістемелік',    6),
('Біліктілікті арттыру курсы',                     'Біліктілік',     3),
('Ашық сабақ / мастер-класс',                      'Әдістемелік',    4),
('Алғыс хат / грамота',                            'Марапат',        2);

-- BATCH
INSERT INTO "Badges" ("BadgeName", "Icon", "Color", "Description", "MinScore") VALUES
('Жаңадан бастаушы',    '🌱', '#66bb6a', 'Алғашқы расталған жетістік',    1),
('Белсенді ұстаз',      '⭐', '#42a5f5', '10 ұпай жинады',                10),
('Тәжірибелі педагог',  '🏅', '#ab47bc', '25 ұпай жинады',                25),
('Мастер ұстаз',        '🥇', '#ffa726', '50 ұпай жинады',                50),
('Алтын ұстаз',         '👑', '#ffd700', '100 ұпай жинады',              100),
('Аңызға айналған',     '💎', '#e91e63', '200 ұпай жинады',              200);

-- BATCH
INSERT INTO "Admins" ("Username", "FullName", "Email", "PasswordHash") VALUES
('admin', 'Жүйе әкімшісі', 'admin@tapsyrma.kz', 'PLACEHOLDER');

-- BATCH
INSERT INTO "Teachers" ("FullName", "Login", "PasswordHash", "Department", "Position", "Email", "TotalScore") VALUES
('Әлиханова Айгүл Бауыржанқызы',   'aigul',  'PLACEHOLDER', 'Ақпараттық технологиялар',  'Аға оқытушы', 'aigul@college.kz',  0),
('Нұрмағанбетов Нұрлан Серікұлы',  'nurlan', 'PLACEHOLDER', 'Математика',                'Оқытушы',     'nurlan@college.kz', 0),
('Сатыбалдиева Динара Мұратқызы',  'dinara', 'PLACEHOLDER', 'Қазақ тілі мен әдебиеті',   'Оқытушы',     'dinara@college.kz', 0),
('Жақыпов Ерлан Асқарұлы',         'erlan',  'PLACEHOLDER', 'Физика',                    'Оқытушы',     'erlan@college.kz',  0),
('Қасымова Мадина Ермекқызы',      'madina', 'PLACEHOLDER', 'Ағылшын тілі',              'Аға оқытушы', 'madina@college.kz', 0),
('Оразбаев Асхат Нұрланұлы',       'askhat', 'PLACEHOLDER', 'Тарих',                     'Оқытушы',     'askhat@college.kz', 0);

-- BATCH
INSERT INTO "Achievements" ("TeacherId", "TypeId", "Title", "Description", "IsApproved", "Score", "ApprovedAt") VALUES
(1, 2, 'Республикалық IT-олимпиада жеңісі',  'Студенттік команданы 1-орынға жеткізді',       TRUE, 10, NOW() - INTERVAL '40 days'),
(1, 5, 'Scopus журналындағы мақала',          '«AI in Education» атты ғылыми мақала',         TRUE,  8, NOW() - INTERVAL '20 days'),
(1, 8, 'BilimLand семинары',                  'Біліктілікті арттыру курсы (40 сағ)',          TRUE,  3, NOW() - INTERVAL '10 days'),
(2, 3, 'Облыстық математика олимпиадасы',     'Жүлделі 2-орын',                               TRUE,  7, NOW() - INTERVAL '30 days'),
(2, 9, 'Ашық сабақ — Интегралды есептеу',     NULL,                                            TRUE,  4, NOW() - INTERVAL '5 days'),
(3, 6, '«Қазақ тілі грамматикасы» мақаласы',  'Облыстық журналда жарияланды',                 TRUE,  5, NOW() - INTERVAL '50 days'),
(4, 4, 'Қалалық физика жарысы',               '3-орын',                                       TRUE,  5, NOW() - INTERVAL '15 days'),
(5, 1, 'IELTS C1 сертификаты',                'Халықаралық тіл сертификаты',                  TRUE, 15, NOW() - INTERVAL '60 days'),
(5, 7, '«English Grammar Guide» оқу құралы',  'Колледж кітапханасында пайдаланылады',         TRUE,  6, NOW() - INTERVAL '25 days'),
(6, 10,'Тарих пәні бойынша алғыс хат',        'Колледж директорынан',                         TRUE,  2, NOW() - INTERVAL '8 days');

-- BATCH
INSERT INTO "Achievements" ("TeacherId", "TypeId", "Title", "Description") VALUES
(2, 5, 'Жаңа ғылыми мақала',              'Жақында жарияланды, растау күтілуде'),
(3, 9, 'Ашық сабақ (көрші колледжде)',    'Ынтымақтастық шеңберінде'),
(4, 8, 'Біліктілікті арттыру курсы',       '120 сағаттық курс');

-- BATCH
INSERT INTO "TeacherBadges" ("TeacherId", "BadgeId")
SELECT t."TeacherId", b."BadgeId"
FROM "Teachers" t
CROSS JOIN "Badges" b
WHERE b."MinScore" <= t."TotalScore";

-- BATCH
INSERT INTO "Events" ("Title", "Description", "EventDate") VALUES
('Ғылыми конференция',  'Жасанды интеллект және білім беру',  NOW() + INTERVAL '14 days'),
('Ашық есік күні',      NULL,                                   NOW() + INTERVAL '30 days'),
('Педагогикалық кеңес', NULL,                                   NOW() + INTERVAL '7 days');
