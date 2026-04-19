-- Seed non-emergency police numbers for major US cities
-- Sources: city police department websites, publicly listed non-emergency lines
-- Users are asked to verify during onboarding — these are best-effort starting points

INSERT INTO non_emergency_numbers (state, city, phone, department, source_url) VALUES
-- California
('CA', 'Los Angeles',       '+12138774275', 'LAPD',                     'https://www.lapdonline.org/contact-us/'),
('CA', 'San Francisco',     '+14155530123', 'SFPD',                     'https://www.sanfranciscopolice.org/get-service/police-records/file-police-report'),
('CA', 'San Diego',         '+16195311500', 'SDPD',                     'https://www.sandiego.gov/police'),
('CA', 'San Jose',          '+14082773211', 'SJPD',                     'https://www.sjpd.org/'),
('CA', 'Sacramento',        '+19162645471', 'Sacramento PD',            'https://www.cityofsacramento.gov/police'),
('CA', 'Oakland',           '+15102383455', 'Oakland PD',               'https://www.oaklandca.gov/departments/police'),
('CA', 'Long Beach',        '+15625707260', 'Long Beach PD',            'https://www.longbeach.gov/police/'),
('CA', 'Fresno',            '+15596214400', 'Fresno PD',                'https://www.fresno.gov/police/'),

-- New York
('NY', 'New York',          '+12126393000', 'NYPD (311 direct)',        'https://www.nyc.gov/site/nypd/'),
('NY', 'Buffalo',           '+17168516790', 'Buffalo PD',               'https://www.bpdny.org/'),
('NY', 'Rochester',         '+15854284013', 'Rochester PD',             'https://www.cityofrochester.gov/police/'),

-- Texas
('TX', 'Houston',           '+17138843131', 'HPD',                      'https://www.houstontx.gov/police/'),
('TX', 'Dallas',            '+12146719500', 'Dallas PD',                'https://dallaspolice.net/'),
('TX', 'San Antonio',       '+12102078230', 'SAPD',                     'https://www.sanantonio.gov/SAPD'),
('TX', 'Austin',            '+15129745000', 'Austin PD',                'https://www.austintexas.gov/department/police'),
('TX', 'Fort Worth',        '+18173924222', 'Fort Worth PD',            'https://police.fortworthtexas.gov/'),
('TX', 'El Paso',           '+19158324400', 'El Paso PD',               'https://www.elpasotexas.gov/police-department/'),

-- Illinois
('IL', 'Chicago',           '+13127464000', 'CPD',                      'https://www.chicagopolice.org/'),

-- Arizona
('AZ', 'Phoenix',           '+16022626151', 'Phoenix PD',               'https://www.phoenix.gov/police'),
('AZ', 'Tucson',            '+15207911444', 'Tucson PD',                'https://www.tucsonaz.gov/police'),

-- Pennsylvania
('PA', 'Philadelphia',      '+12156861776', 'Philadelphia PD',          'https://www.phillypolice.com/'),
('PA', 'Pittsburgh',        '+14122556610', 'Pittsburgh PD',            'https://pittsburghpa.gov/police/'),

-- Florida
('FL', 'Miami',             '+13055795000', 'Miami PD',                 'https://www.miami-police.org/'),
('FL', 'Orlando',           '+13212354357', 'Orlando PD',               'https://www.orlando.gov/Our-Government/Departments-Offices/Orlando-Police-Department'),
('FL', 'Tampa',             '+18132316130', 'Tampa PD',                 'https://www.tampagov.net/police'),
('FL', 'Jacksonville',      '+19046301529', 'JSO',                      'https://www.jaxsheriff.org/'),

-- Ohio
('OH', 'Columbus',          '+16146454545', 'Columbus PD',              'https://www.columbus.gov/police/'),
('OH', 'Cleveland',         '+12166215000', 'Cleveland PD',             'https://www.clevelandohio.gov/CityofCleveland/Home/Government/CityAgencies/PublicSafety/Police'),
('OH', 'Cincinnati',        '+15137651212', 'Cincinnati PD',            'https://www.cincinnati-oh.gov/police/'),

-- Georgia
('GA', 'Atlanta',           '+14046144545', 'Atlanta PD',               'https://www.atlantapd.org/'),

-- North Carolina
('NC', 'Charlotte',         '+17043367600', 'CMPD',                     'https://charlottenc.gov/CMPD/'),
('NC', 'Raleigh',           '+19199966000', 'Raleigh PD',               'https://raleighnc.gov/police'),

-- Michigan
('MI', 'Detroit',           '+13132671212', 'Detroit PD',               'https://detroitmi.gov/departments/police-department'),

-- Washington
('WA', 'Seattle',           '+12066255011', 'Seattle PD',               'https://www.seattle.gov/police'),

-- Colorado
('CO', 'Denver',            '+17207201311', 'Denver PD',                'https://www.denvergov.org/Government/Departments/Department-of-Public-Safety/Police'),

-- Massachusetts
('MA', 'Boston',            '+16173434484', 'Boston PD',                'https://www.boston.gov/departments/police'),

-- Tennessee
('TN', 'Nashville',         '+16158624600', 'Nashville PD',             'https://www.nashville.gov/departments/police'),
('TN', 'Memphis',           '+19015455300', 'Memphis PD',               'https://www.memphispolice.org/'),

-- Oregon
('OR', 'Portland',          '+15038234000', 'Portland PD',              'https://www.portland.gov/police'),

-- Nevada
('NV', 'Las Vegas',         '+17023113111', 'LVMPD',                    'https://www.lvmpd.com/'),

-- Missouri
('MO', 'Kansas City',       '+18162343000', 'KCPD',                     'https://www.kcpd.org/'),
('MO', 'St. Louis',         '+13142316130', 'SLMPD',                    'https://www.slmpd.org/'),

-- Maryland
('MD', 'Baltimore',         '+14103962525', 'Baltimore PD',             'https://www.baltimorepolice.org/'),

-- Wisconsin
('WI', 'Milwaukee',         '+14149335735', 'Milwaukee PD',             'https://city.milwaukee.gov/police'),

-- Minnesota
('MN', 'Minneapolis',       '+16126735000', 'Minneapolis PD',           'https://www.minneapolismn.gov/government/departments/police/'),

-- Indiana
('IN', 'Indianapolis',      '+13173271282', 'IMPD',                     'https://www.indy.gov/agency/indianapolis-metropolitan-police-department'),

-- District of Columbia
('DC', 'Washington',        '+12027371000', 'MPD',                      'https://mpdc.dc.gov/'),

-- Louisiana
('LA', 'New Orleans',       '+15048213000', 'NOPD',                     'https://nola.gov/nopd/'),

-- Kentucky
('KY', 'Louisville',        '+15025742111', 'Louisville Metro PD',      'https://louisvilleky.gov/government/louisville-metro-police-department'),

-- Oklahoma
('OK', 'Oklahoma City',     '+14052315000', 'OKCPD',                    'https://www.okc.gov/departments/police')

ON CONFLICT DO NOTHING;
