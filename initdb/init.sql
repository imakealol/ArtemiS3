CREATE TABLE file_tags (
    hashed_key VARCHAR(255) PRIMARY KEY,
    bucket VARCHAR(255) NOT NULL,
    tags VARCHAR(255) ARRAY
);

CREATE TABLE custom_mime_types (
    extension VARCHAR(255) PRIMARY KEY,
    mime_type VARCHAR(255) NOT NULL
);

INSERT INTO custom_mime_types (extension, mime_type) VALUES ('lbl', 'text/lbl');
INSERT INTO custom_mime_types (extension, mime_type) VALUES ('lab', 'text/lab');
INSERT INTO custom_mime_types (extension, mime_type) VALUES ('geojson', 'application/geo+json');
INSERT INTO custom_mime_types (extension, mime_type) VALUES ('kmz', 'application/vnd.google-earth.kmz');
INSERT INTO custom_mime_types (extension, mime_type) VALUES ('kml', 'application/vnd.google-earth.kml+xml');