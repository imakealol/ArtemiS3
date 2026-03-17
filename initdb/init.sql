CREATE TABLE file_tags (
    hashed_key VARCHAR(255) PRIMARY KEY,
    bucket VARCHAR(255) NOT NULL,
    tags VARCHAR(255) ARRAY
)